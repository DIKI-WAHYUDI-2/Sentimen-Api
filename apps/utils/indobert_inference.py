import logging
import os
import re
from functools import lru_cache

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "model")
LABEL_MAP_PATH = os.path.join(MODEL_DIR, "label_map.csv")
MAX_LENGTH = 512

print(BASE_DIR)
print(MODEL_DIR)
print(LABEL_MAP_PATH)

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"[^\w\s\.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@lru_cache(maxsize=1)
def _load_label_map():
    dataframe = pd.read_csv(LABEL_MAP_PATH)
    return {
        int(row["label_id"]): str(row["label_name"]).strip().lower()
        for _, row in dataframe.iterrows()
    }


@lru_cache(maxsize=1)
def _load_model_components():
    logger.info("Loading IndoBERT model for sentiment inference", extra={"path": MODEL_DIR})
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()
    return tokenizer, model, _load_label_map()


def analyze_sentiment(title: str, content: str | None = None) -> str:
    tokenizer, model, label_map = _load_model_components()

    cleaned_title = clean_text(title)
    cleaned_content = clean_text(content or "")
    if not cleaned_content:
        cleaned_content = cleaned_title

    encoded = tokenizer(
        cleaned_title,
        cleaned_content,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )

    with torch.no_grad():
        logits = model(**encoded).logits
        prediction = int(torch.argmax(logits, dim=-1).item())

    return label_map.get(prediction, model.config.id2label.get(prediction, "netral")).lower()
