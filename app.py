from flask import Flask, jsonify, request
import joblib
from scraper import get_news
from model import analyze_sentiment
from db_connection import insert_berita, get_news_paginated, change_sentiment_by_id,search_news_by_title,get_sentimen_data,add_berita_data, login,get_news_count
from flask_cors import CORS
import jwt
import datetime
import sys

SECRET_KEY = 'rahasia'

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", supports_credentials=True)

# Endpoint untuk mengambil berita dan melakukan analisis sentimen
@app.route("/analyze", methods=["GET"])
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

@app.route("/news", methods=["GET", "OPTIONS"])
def get_news():
    page = request.args.get('page', default=1, type=int) 
    limit = request.args.get('limit', default=10, type=int)
    try:
        print("Request Headers:", dict(request.headers), file=sys.stderr)
        print("Request Args:", request.args, file=sys.stderr)
        print("Page:", page, "Limit:", limit, file=sys.stderr)

        page = int(request.args.get("page", 1) or 1)
        limit = int(request.args.get("limit", 10) or 10)

        news_data = get_news_paginated(page, limit)
        total_news = get_news_count()
        total_pages = (total_news + limit - 1) // limit

        return jsonify({
            "success": True,
            "news": news_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_news,
                "items_per_page": limit
            }
        }), 200

    except Exception as e:
        print("Error:", str(e), file=sys.stderr)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
@app.route('/change-sentiment', methods=['POST'])
def change_sentiment_api():
    try:
        data = request.json
        berita_id = data.get("id") 
        new_sentiment = data.get("sentimen")

        if not berita_id or not new_sentiment:
            return jsonify({"error": "ID dan Sentimen harus diberikan"}), 400

        # Panggil fungsi update_sentiment()
        success = change_sentiment_by_id(berita_id, new_sentiment)
        
        if success:
            return jsonify({"message": "Sentimen berita berhasil diubah"}), 200
        else:
            return jsonify({"error": "Gagal mengubah sentimen"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/search", methods=['GET'])
def search_news():
    try:
        query = request.args.get("q", "").strip()

        if not query:
            return jsonify({"error": "Query pencarian tidak boleh kosong!"})    
        
        results = search_news_by_title(query)

        if not results:
            return jsonify({"message": "Berita tidak ditemukan!"}), 404  

        return jsonify(results), 200      
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sentimen", methods=['GET'])
def get_sentimen():
    try:
        results = get_sentimen_data()

        if not results:
            return jsonify({"message": "Sentimen tidak ditemukan!"}), 404  
    
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/berita", methods = ['POST'])
def add_berita():
    try:
        data = request.json
        add_berita_data(data)
        if not data:
            return jsonify({"message": "Data tidak boleh kosong!"}), 404    
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}),500

@app.route("/login", methods = ['POST'])
def login_system():
    try:
        data = request.json

        result = login(data)

        if not data:
            return jsonify({"status": "error", "message": "Data tidak boleh kosong!"})

        if result["status"] != "ok":
            return jsonify(result), 401

        # Generate token
        token = jwt.encode({
            'username': data['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')

        # Set token ke cookie
        response = jsonify({"status": "ok", "message": "Berhasil login"})
        response.set_cookie(
            'token',
            token,
            httponly=True,
            samesite='Lax',
            secure=False  
        )

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500     

@app.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"status": "ok", "message": "Berhasil logout"})
    response.set_cookie('token', '', expires=0) 
    return response
    
if __name__ == "__main__":
    app.run(debug=True)
