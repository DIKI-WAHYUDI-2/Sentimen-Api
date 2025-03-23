from flask import Flask, jsonify
import joblib
from scraper import get_news
from model import analyze_sentiment
from db_connection import insert_berita

app = Flask(__name__)  

# Endpoint untuk mengambil berita dan melakukan analisis sentimen
@app.route("/news", methods=["GET"])
def get_and_analyze_news():
    print("Mengambil berita terbaru...")
    news_data = get_news()

    if not news_data:
        return jsonify({"error": "Tidak ada berita yang ditemukan."}), 404
    
    for news in news_data:
        try:
            news["sentiment"] = analyze_sentiment(news["title"])
            source_name = news["source"]["name"] if isinstance(news["source"], dict) else str(news["source"])

            # Gunakan nilai default jika data kosong
            title = news.get('title', 'Judul Tidak Tersedia')
            date = news.get('date', '2025-01-01')  # Default tanggal jika tidak ada
            source = source_name
            link = news.get('link', '#')
            meta_title = news.get('meta_title', 'Title Tidak Tersedia')
            meta_description = news.get('meta_description', 'Deskripsi Tidak Tersedia')
            sentiment = news['sentiment']

            insert_berita(title, date, source, link, meta_title, meta_description, sentiment)

        except Exception as e:
            print(f"Error saat memproses berita: {e}")

    return jsonify({"news": news_data}), 200

if __name__ == "__main__":
    app.run(debug=True)
