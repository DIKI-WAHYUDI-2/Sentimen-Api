from apps.models.news import News
from apps.app import db
from sqlalchemy import func

class NewsRepository:

    @staticmethod
    def save(data):
        news = News(**data)
        db.session.add(news)
        db.session.commit()
        return news

    @staticmethod
    def find_all():
        news = News.query.all()
        return news

    @staticmethod
    def find_by_id(id):
        news = News.query.get(id)
        return news

    @staticmethod
    def delete_news(id):
        news = News.query.get(id)
        db.session.delete(news)
        db.session.commit()
        return news

    @staticmethod
    def find_by_keyword(keyword):
        pattern = f"%{keyword}%"
        print(f"[DEBUG] Pattern pencarian: {pattern}")
        return News.query.filter(News.judul.ilike(pattern)).all()

    @staticmethod
    def get_sentimen_data():
        try:
            # Query: SELECT sentimen, COUNT(*) FROM berita GROUP BY sentimen
            results = db.session.query(
                News.sentimen,
                func.count(News.sentimen)
            ).group_by(News.sentimen).all()

            # Bentuk hasilnya jadi list of dict
            data = [{"name": sentimen.capitalize(), "value": count} for sentimen, count in results]
            return data
        except Exception as e:
            print(f"Error data tidak ditemukan: {e}")
            return []

    @staticmethod
    def get_sentimen_and_date():
        try:
            # Ambil tanggal dan sentimen semua berita
            results = db.session.query(
                func.date(News.tanggal).label('tanggal'),
                News.sentimen
            ).all()
            return results
        except Exception as e:
            print(f"Error data tidak ditemukan: {e}")
            return []