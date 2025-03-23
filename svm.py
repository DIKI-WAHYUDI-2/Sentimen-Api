from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
import joblib

# Membaca file Excel
# df = pd.read_excel("./data/data-berita.xlsx", sheet_name=None)

# # Asumsikan sheet pertama adalah train dan sheet kedua adalah test
# sheet_names = list(df.keys())
# df_train = df[sheet_names[0]]
# df_test = df[sheet_names[1]]

df_train = pd.read_csv("./data/train_data.csv")  
df_test = pd.read_csv("./data/test_data.csv")  

# Gabungkan judul dan isi berita sebagai fitur
X_train = df_train["title"]
y_train = df_train["Sentimen"]

X_test = df_test["title"]
y_test = df_test["Sentimen"]

# Pastikan tidak ada NaN di X_train dan X_test
X_train = X_train.fillna("")  # Ganti NaN dengan string kosong
X_test = X_test.fillna("")  

# # TF-IDF Vectorization
vectorizer = TfidfVectorizer(ngram_range=(1, 2))
X_train_vectorized = vectorizer.fit_transform(X_train)
X_test_vectorized = vectorizer.transform(X_test)

# # Latih model SVM
svm = SVC(kernel='linear')
svm.fit(X_train_vectorized, y_train)

# # Simpan model dan vectorizer
joblib.dump(svm, "./model/svm_model.pkl")
joblib.dump(vectorizer, "./model/vectorizer.pkl")

# # Prediksi
y_pred_svm = svm.predict(X_test_vectorized)

# # Evaluasi Model SVM
print("Akurasi SVM:", accuracy_score(y_test, y_pred_svm))
print("\nLaporan Klasifikasi SVM:")
print(classification_report(y_test, y_pred_svm))

# # Confusion Matrix
conf_matrix = confusion_matrix(y_test, y_pred_svm)
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=['Negatif', 'Netral', 'Positif'], yticklabels=['Negatif', 'Netral', 'Positif'])
plt.xlabel("Predicted Label")
plt.ylabel("True Label")
plt.title("Confusion Matrix - SVM")
plt.show()
