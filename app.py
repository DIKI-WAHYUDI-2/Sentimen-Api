from flask import Flask, jsonify, request
import joblib
from scraper import get_news
from model import analyze_sentiment
from db_connection import insert_berita, get_news_paginated, change_sentiment_by_id,search_news_by_title,get_sentimen_data,add_berita_data, login,get_news_count,get_sentimen_and_date
from flask_cors import CORS
import jwt
from datetime import datetime, timedelta, timezone
import sys
from collections import defaultdict 

SECRET_KEY = 'rahasia'

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", supports_credentials=True)

# Endpoint untuk mengambil berita dan melakukan analisis sentimen
@app.route("/analyze", methods=["POST"])
def get_and_analyze_news():
    print("Mengambil berita terbaru...")
    data = request.json
    news_data = get_news(data)

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

            # insert_berita(title, date, source, link, meta_title, meta_description, sentiment)

        except Exception as e:
            print(f"Error saat memproses berita: {e}")

    return jsonify({"news": news_data}), 200

@app.route("/news", methods=["GET"])
def get_news_data():
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
        

        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        

        results = get_sentimen_data()
        

        if not results:
            return jsonify({"message": "Sentimen tidak ditemukan!"}), 404  

        return jsonify(results), 200
    except Exception as e:
        
        return jsonify({"error": str(e)}), 500


@app.route("/sentimen-bulanan", methods = ['GET'])
def get_sentimen_bulanan():

    bulan_map = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    try:
        data_berita = get_sentimen_and_date()
        print(data_berita)
        # Mengelompokkan berita per bulan dan menghitung jenis sentimen (positif, negatif, netral)
        sentimen_per_bulan = defaultdict(lambda: {"positif": 0, "negatif": 0, "netral": 0})

        for berita in data_berita:
            tanggal = datetime.strptime(berita[0], "%Y-%m-%d")
            bulan = tanggal.month
            sentimen = berita[1].strip().lower() 

            if sentimen == "positif":
                sentimen_per_bulan[bulan]["positif"] += 1
            elif sentimen == "negatif":
                sentimen_per_bulan[bulan]["negatif"] += 1
            else:
                sentimen_per_bulan[bulan]["netral"] += 1

        # Menyiapkan hasil untuk dikembalikan dalam format JSON sesuai permintaan
        hasil = []
        for bulan, sentimen_count in sentimen_per_bulan.items():
            hasil.append({
                "bulan": bulan_map[bulan],
                "positif": sentimen_count["positif"],
                "netral": sentimen_count["netral"],
                "negatif": sentimen_count["negatif"]
            })
        
        # Membungkus hasil dalam objek "per_bulan"
        return jsonify({"per_bulan": hasil}), 200

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
        print(data)
        print(result)

        if not data:
            return jsonify({"status": "error", "message": "Data tidak boleh kosong!"})

        if result["status"] != "ok":
            return jsonify(result), 401

        # Generate token
        token = jwt.encode({
            'username': data['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=1)
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
    app.run(debug=True, threaded=True)