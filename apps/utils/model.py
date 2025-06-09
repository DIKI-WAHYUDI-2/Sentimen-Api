import joblib
import os

current_dir = os.path.dirname(__file__)
svm_path = os.path.join(current_dir, "svm_model.pkl")
vectorizer_path = os.path.join(current_dir, "vectorizer.pkl")
# Load Model & Vectorizer
try:
    svm = joblib.load(svm_path)
    vectorizer = joblib.load(vectorizer_path)
except Exception as e:
    print(f"Error loading model: {e}")
    svm, vectorizer = None, None  

def analyze_sentiment(text):
    if not text.strip():
        return "Tidak Diketahui"
        
    if svm is None or vectorizer is None:
        return "Model tidak tersedia"

    text_vectorized = vectorizer.transform([text])
    sentiment = svm.predict(text_vectorized)[0]
    return sentiment
