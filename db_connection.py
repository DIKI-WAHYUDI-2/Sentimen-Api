import mysql.connector
import bcrypt


# Konfigurasi koneksi ke database
db = mysql.connector.connect(
    host="localhost",      
    user="root",           
    password="root",      
    database="sentimen_berita"
)

print("Koneksi berhasil!")

def insert_berita(judul, tanggal, sumber, link, meta_title, meta_description, sentiment):

    cursor = db.cursor()  
    sql = """
    INSERT INTO berita (judul, tanggal, sumber, link, meta_title, meta_description, sentimen) 
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (judul, tanggal, sumber, link, meta_title, meta_description, sentiment)
    
    cursor.execute(sql, values)
    db.commit()
    cursor.close() 
    print("Berita berhasil disimpan!")

def get_all_news(page=1, limit=10):
    offset = (page - 1) * limit
    cursor = db.cursor(dictionary=True)
    sql = """
        SELECT id, judul, DATE_FORMAT(tanggal, '%Y-%m-%d') as tanggal, sumber, link, meta_title, meta_description, sentimen
        FROM berita
        ORDER BY tanggal DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql, (limit, offset))
    result = cursor.fetchall()
    cursor.close()
    return result

def get_news_paginated(page=1, limit=10):
    offset = (page - 1) * limit
    cursor = db.cursor(dictionary=True)
    sql = """
        SELECT id, judul, DATE_FORMAT(tanggal, '%Y-%m-%d') as tanggal, sumber, link, meta_title, meta_description, sentimen
        FROM berita
        ORDER BY tanggal DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql, (limit, offset))
    result = cursor.fetchall()
    cursor.close()
    return result

def get_news_count():
    cursor = db.cursor()
    sql = "SELECT COUNT(*) as total FROM berita"
    cursor.execute(sql)
    result = cursor.fetchone()
    cursor.close()
    return result[0]

def change_sentiment_by_id(berita_id, new_sentiment):
    try:
        cursor = db.cursor()
        sql = """UPDATE berita SET sentimen = %s WHERE id = %s"""
        cursor.execute(sql, (new_sentiment, berita_id))  # Gunakan parameterized query
        db.commit()
        cursor.close()
        print(f"Sentimen berita dengan ID {berita_id} berhasil diganti menjadi '{new_sentiment}'")
        return True
    except Exception as e:
        print(f"Error saat mengganti sentimen: {e}")
        return False

def search_news_by_title(judul):
    try:
        cursor = db.cursor()
        sql = "SELECT * FROM berita WHERE judul LIKE %s"
        cursor.execute(sql,(f"%{judul}%",))
        result = cursor.fetchall()
        db.commit()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error judul tidak ditemukan: {e}")

def get_sentimen_data():
    try:
        cursor = db.cursor()
        sql = """
        SELECT sentimen, COUNT(*) as total
        FROM berita
        GROUP BY sentimen
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        db.commit()
        cursor.close()

        data = [{"name": row[0].capitalize(), "value": row[1]} for row in results]

        return data
    except Exception as e:
        print(f"Error data tidak ditemukan: {e}")

def add_berita_data(berita):
    try:
        cursor = db.cursor()
        sql = """
        INSERT INTO berita(judul,tanggal,sumber,link,sentimen) VALUES (%s,%s,%s,%s,%s)
        """
        data = berita

        values = (
            berita['judul'],
            berita['tanggal'],
            berita['sumber'],
            berita['link'],
            berita['sentimen']
        )
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        return {"status": "ok", "message": "Data berhasil ditambahkan"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

def login(user):
    try:
        cursor = db.cursor(dictionary=True)
        
        # Ambil user berdasarkan username/email
        cursor.execute("SELECT * FROM users WHERE username = %s", (user['username'],))
        result = cursor.fetchone()

        if not result:
            return {"status": "error", "message": "Username tidak ditemukan"}

        stored_hash = result['password']

        # Bandingkan hash password
        if bcrypt.checkpw(user['password'].encode(), stored_hash.encode()):
            return {"status": "ok", "message": "Berhasil Login"}
        else:
            return {"status": "error", "message": "Password salah"}

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}
    