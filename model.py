import joblib

# Load Model & Vectorizer
try:
    svm = joblib.load("./model/svm_model.pkl")
    vectorizer = joblib.load("./model/vectorizer.pkl")
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
