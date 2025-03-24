import mysql.connector

# Konfigurasi koneksi ke database
db = mysql.connector.connect(
    host="localhost",      # Ganti dengan host MySQL kamu
    user="root",           # Ganti dengan username MySQL kamu
    password="root",       # Ganti dengan password MySQL kamu
    database="sentimen_berita"  # Ganti dengan nama database kamu
)

print("Koneksi berhasil!")

def insert_berita(judul, tanggal, sumber, link, meta_title, meta_description, sentiment):
    cursor = db.cursor()  # Buat cursor di dalam fungsi agar aman
    sql = """
    INSERT INTO berita (judul, tanggal, sumber, link, meta_title, meta_description, sentimen) 
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (judul, tanggal, sumber, link, meta_title, meta_description, sentiment)
    
    cursor.execute(sql, values)
    db.commit()
    cursor.close()  # Tutup cursor setelah dipakai
    print("Berita berhasil disimpan!")

def get_all_news():
    cursor = db.cursor(dictionary=True) 
    sql = "SELECT * FROM berita"
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    return result 
