"""
Analisis sentimen berita Bahasa Indonesia menggunakan IndoBERT.
Pipeline ini memakai HuggingFace Trainer API dengan validation split,
early stopping, evaluasi per epoch, dan penyimpanan model terbaik.
"""

import json
import os
import random
import re
import warnings
from collections import Counter

import numpy as np
import pandas as pd
import torch
import transformers
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import Dataset
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

warnings.filterwarnings("ignore")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")


# ============================================================
# KONFIGURASI
# ============================================================
BASE_DIR = r"D:\PROGRAMMING\Analisis Sentimen"
DATA_PATH = os.path.join(BASE_DIR, "data", "dataset-berita.xlsx")
MODEL_DIR = os.path.join(BASE_DIR, "model")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "checkpoints")
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
PRETRAINED = "indobenchmark/indobert-base-p1"

COL_JUDUL = "Judul"
COL_ISI = "Isi Berita"
COL_LABEL = "Sentimen"

MAX_LENGTH = 512
BATCH_SIZE = 16
EPOCHS = 20                      # dinaikkan dari 15, early stopping tetap jaga
LEARNING_RATE = 2e-5             # dinaikkan dari 1e-5 (sweet spot fine-tuning BERT)
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
EARLY_STOPPING_PATIENCE = 5  
VAL_LOSS_THRESHOLD = 0.30
TEST_SIZE = 0.15
VAL_SIZE = 0.15
SEED = 42

# Opsi advanced improvement
USE_AUGMENTATION = True          # diaktifkan untuk variasi data training
AUGMENTATION_PROBABILITY = 0.35  # dinaikkan dari 0.25
USE_CLASS_WEIGHTS = True         # diaktifkan untuk perkuat kelas netral

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

set_seed(SEED)
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# UTILITAS
# ============================================================
def print_section(title: str) -> None:
    print("=" * 70)
    print(title)
    print("=" * 70)


def clean_text(text: str) -> str:
    """
    Preprocessing ringan agar informasi penting untuk BERT tidak banyak hilang.
    Hindari menghapus semua tanda baca/angka secara agresif karena kadang
    informasi tersebut membantu klasifikasi berita.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    # Hapus emoji dan simbol unicode yang tidak relevan
    text = re.sub(r"[^\w\s\.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def augment_text(text: str, probability: float = 0.25) -> str:
    """
    Augmentasi sederhana untuk Bahasa Indonesia tanpa dependency tambahan:
    random deletion ringan dan local swap. Dipakai hanya pada train split.
    """
    if random.random() > probability:
        return text

    words = text.split()
    if len(words) < 6:
        return text

    augmented_words = []
    for word in words:
        if len(word) > 3 and random.random() < 0.08:
            continue
        augmented_words.append(word)

    if len(augmented_words) >= 4 and random.random() < 0.5:
        idx = random.randint(0, len(augmented_words) - 2)
        augmented_words[idx], augmented_words[idx + 1] = (
            augmented_words[idx + 1],
            augmented_words[idx],
        )

    augmented_text = " ".join(augmented_words).strip()
    return augmented_text if augmented_text else text


def apply_augmentation(titles, contents, labels):
    augmented_titles = []
    augmented_contents = []
    augmented_labels = []
    for title, content, label in zip(titles, contents, labels):
        augmented_titles.append(augment_text(title, probability=AUGMENTATION_PROBABILITY))
        augmented_contents.append(augment_text(content, probability=AUGMENTATION_PROBABILITY))
        augmented_labels.append(label)
    return (
        titles + augmented_titles,
        contents + augmented_contents,
        labels + augmented_labels,
    )


def save_json(filepath: str, payload: dict) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def to_serializable(obj):
    if isinstance(obj, dict):
        return {key: to_serializable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    if isinstance(obj, tuple):
        return [to_serializable(item) for item in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


class BeritaDataset(Dataset):
    def __init__(self, titles, contents, labels, tokenizer, max_length):
        self.titles = list(titles)
        self.contents = list(contents)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.titles[idx],
            self.contents[idx],
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoding.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        if self.class_weights is not None:
            loss_fct = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device))
        else:
            loss_fct = torch.nn.CrossEntropyLoss()

        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss

class ValLossThresholdCallback(transformers.TrainerCallback):
    """Hentikan training jika val loss sudah mencapai nilai target."""

    def __init__(self, threshold: float):
        self.threshold = threshold

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        val_loss = metrics.get("eval_loss") if metrics else None
        if val_loss is not None and val_loss <= self.threshold:
            print(
                f"\n[ValLossThreshold] Val loss {val_loss:.4f} ≤ "
                f"{self.threshold} → training dihentikan."
            )
            control.should_training_stop = True
        return control

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        preds,
        average="macro",
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1,
        "precision_macro": precision,
        "recall_macro": recall,
    }


# ============================================================
# 1. LOAD DATASET
# ============================================================
print_section("1. LOAD DATASET")

df = pd.read_excel(DATA_PATH)
df = df[[COL_JUDUL, COL_ISI, COL_LABEL]].copy()
df = df.dropna(subset=[COL_LABEL]).reset_index(drop=True)
df[COL_JUDUL] = df[COL_JUDUL].fillna("")
df[COL_ISI] = df[COL_ISI].fillna("")

print(f"Shape dataset   : {df.shape}")
print(f"Kolom           : {list(df.columns)}")
print(f"Distribusi label:\n{df[COL_LABEL].value_counts()}\n")


# ============================================================
# 2. PREPROCESSING
# ============================================================
print_section("2. PREPROCESSING")

df["judul_bersih"] = df[COL_JUDUL].apply(clean_text)
df["isi_bersih"] = df[COL_ISI].apply(clean_text)
df["teks"] = (df["judul_bersih"] + " " + df["isi_bersih"]).str.strip()

print(f"Contoh teks setelah preprocessing:\n{df['teks'].iloc[0][:300]}\n")


# ============================================================
# 3. ENCODE LABEL
# ============================================================
print_section("3. ENCODE LABEL")

label_encoder = LabelEncoder()
df["label_enc"] = label_encoder.fit_transform(df[COL_LABEL])
label_names = list(label_encoder.classes_)
num_labels = len(label_names)
label2id = {label: idx for idx, label in enumerate(label_names)}
id2label = {idx: label for label, idx in label2id.items()}

print(f"Label asli      : {label_names}")
print(f"Label encoded   : {list(range(num_labels))}\n")


# ============================================================
# 4. SPLIT DATASET
# ============================================================
print_section("4. SPLIT DATASET (train / validation / test)")

train_df, temp_df = train_test_split(
    df[["judul_bersih", "isi_bersih", "label_enc"]],
    test_size=TEST_SIZE + VAL_SIZE,
    random_state=SEED,
    stratify=df["label_enc"],
)

relative_val_size = VAL_SIZE / (TEST_SIZE + VAL_SIZE)
val_df, test_df = train_test_split(
    temp_df,
    test_size=1 - relative_val_size,
    random_state=SEED,
    stratify=temp_df["label_enc"],
)

X_train_title = train_df["judul_bersih"].tolist()
X_train_content = train_df["isi_bersih"].tolist()
y_train = train_df["label_enc"].tolist()
X_val_title = val_df["judul_bersih"].tolist()
X_val_content = val_df["isi_bersih"].tolist()
y_val = val_df["label_enc"].tolist()
X_test_title = test_df["judul_bersih"].tolist()
X_test_content = test_df["isi_bersih"].tolist()
y_test = test_df["label_enc"].tolist()

if USE_AUGMENTATION:
    X_train_title, X_train_content, y_train = apply_augmentation(
        X_train_title,
        X_train_content,
        y_train,
    )
    print(f"Distribusi train setelah augmentasi: {Counter(y_train)}")

print(f"Train      : {len(X_train_title)} sampel")
print(f"Validation : {len(X_val_title)} sampel")
print(f"Test       : {len(X_test_title)} sampel\n")


# ============================================================
# 5. TOKENISASI
# ============================================================
print_section("5. TOKENISASI (IndoBERT)")

tokenizer = AutoTokenizer.from_pretrained(PRETRAINED)
data_collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8)

train_dataset = BeritaDataset(
    X_train_title,
    X_train_content,
    y_train,
    tokenizer,
    MAX_LENGTH,
)
val_dataset = BeritaDataset(
    X_val_title,
    X_val_content,
    y_val,
    tokenizer,
    MAX_LENGTH,
)
test_dataset = BeritaDataset(
    X_test_title,
    X_test_content,
    y_test,
    tokenizer,
    MAX_LENGTH,
)

print("Tokenizer dan dataset siap.\n")


# ============================================================
# 6. LOAD MODEL
# ============================================================
print_section("6. LOAD MODEL INDOBERT")

model_config = AutoConfig.from_pretrained(
    PRETRAINED,
    num_labels=num_labels,
    id2label=id2label,
    label2id=label2id,
)

model = AutoModelForSequenceClassification.from_pretrained(
    PRETRAINED,
    config=model_config,
    ignore_mismatched_sizes=True,
)

print(f"Model dimuat    : {PRETRAINED}")
print(f"Jumlah label    : {num_labels}\n")


# ============================================================
# 7. SIAPKAN CLASS WEIGHTS OPSIONAL
# ============================================================
print_section("7. PERSIAPAN TRAINING")

class_weights = None
label_counts = Counter(y_train)
print(f"Distribusi train: {label_counts}")

if USE_CLASS_WEIGHTS:
    total = sum(label_counts.values())
    weights = [total / (num_labels * label_counts[idx]) for idx in range(num_labels)]
    class_weights = torch.tensor(weights, dtype=torch.float)
    print(f"Class weights   : {weights}")
else:
    print("Class weights   : tidak digunakan (dataset relatif seimbang)")

print(f"Augmentasi teks : {'aktif' if USE_AUGMENTATION else 'nonaktif'}\n")


# ============================================================
# 8. TRAINING
# ============================================================
print_section("8. TRAINING")

training_args = TrainingArguments(
    output_dir=CHECKPOINT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    warmup_ratio=WARMUP_RATIO,
    lr_scheduler_type="cosine",
    label_smoothing_factor=0.1,  # bantu model tidak terlalu overconfident
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
    greater_is_better=True,
    logging_dir=LOG_DIR,
    logging_strategy="epoch",
    seed=SEED,
    fp16=torch.cuda.is_available(),
    report_to="none",
)

trainer = WeightedTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=data_collator,
    processing_class=tokenizer,
    compute_metrics=compute_metrics,
    class_weights=class_weights,
    callbacks=[
        EarlyStoppingCallback(
            early_stopping_patience=EARLY_STOPPING_PATIENCE,
            early_stopping_threshold=0.001,
        ),
        ValLossThresholdCallback(threshold=VAL_LOSS_THRESHOLD)
    ],
)

train_result = trainer.train(resume_from_checkpoint=True)
trainer.save_model(MODEL_DIR)
tokenizer.save_pretrained(MODEL_DIR)

print("\nTraining selesai.")
print(f"Best checkpoint : {trainer.state.best_model_checkpoint}")
print(f"Best metric     : {trainer.state.best_metric}\n")


# ============================================================
# 9. EVALUASI FINAL PADA TEST SET
# ============================================================
print_section("9. EVALUASI FINAL PADA TEST SET")

# Gunakan predict() saja — sudah mencakup metrics dari compute_metrics
predictions = trainer.predict(test_dataset)
y_pred = np.argmax(predictions.predictions, axis=-1)
eval_metrics = predictions.metrics

test_accuracy = accuracy_score(y_test, y_pred)
test_f1_macro = f1_score(y_test, y_pred, average="macro")
report_dict = classification_report(
    y_test,
    y_pred,
    target_names=label_names,
    zero_division=0,
    output_dict=True,
)
report_text = classification_report(
    y_test,
    y_pred,
    target_names=label_names,
    zero_division=0,
)
cm = confusion_matrix(y_test, y_pred)

print(f"Test accuracy   : {test_accuracy:.4f} ({test_accuracy * 100:.2f}%)")
print(f"Test f1 macro   : {test_f1_macro:.4f}\n")
print("Classification report:")
print(report_text)
print("Confusion matrix:")
print(pd.DataFrame(cm, index=label_names, columns=label_names))


# ============================================================
# 10. SIMPAN HASIL
# ============================================================
print_section("10. SIMPAN MODEL DAN LAPORAN")

pd.DataFrame(
    {
        "label_id": list(id2label.keys()),
        "label_name": list(id2label.values()),
    }
).to_csv(os.path.join(MODEL_DIR, "label_map.csv"), index=False)

pd.DataFrame(cm, index=label_names, columns=label_names).to_csv(
    os.path.join(REPORT_DIR, "confusion_matrix.csv")
)

with open(os.path.join(REPORT_DIR, "classification_report.txt"), "w", encoding="utf-8") as file:
    file.write(report_text)

save_json(os.path.join(REPORT_DIR, "classification_report.json"), to_serializable(report_dict))
save_json(
    os.path.join(REPORT_DIR, "test_metrics.json"),
    to_serializable({
        "test_accuracy": test_accuracy,
        "test_f1_macro": test_f1_macro,
        "eval_metrics": eval_metrics,
        "train_metrics": train_result.metrics,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "best_metric": trainer.state.best_metric,
        "config": {
            "pretrained_model": PRETRAINED,
            "max_length": MAX_LENGTH,
            "batch_size": BATCH_SIZE,
            "epochs": EPOCHS,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "scheduler": "cosine",
            "warmup_ratio": WARMUP_RATIO,
            "early_stopping_patience": EARLY_STOPPING_PATIENCE,
            "val_loss_threshold": VAL_LOSS_THRESHOLD,
            "use_augmentation": USE_AUGMENTATION,
            "use_class_weights": USE_CLASS_WEIGHTS,
            "seed": SEED,
        },
        "library_versions": {
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
    }),
)

print(f"Model disimpan ke         : {MODEL_DIR}")
print(f"Tokenizer disimpan ke     : {MODEL_DIR}")
print(f"Label map disimpan ke     : {os.path.join(MODEL_DIR, 'label_map.csv')}")
print(f"Confusion matrix disimpan : {os.path.join(REPORT_DIR, 'confusion_matrix.csv')}")
print(f"Classification report     : {os.path.join(REPORT_DIR, 'classification_report.txt')}")
print(f"Metrics JSON              : {os.path.join(REPORT_DIR, 'test_metrics.json')}")
print("\nSelesai.")
