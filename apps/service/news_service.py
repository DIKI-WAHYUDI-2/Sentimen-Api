from apps.repositories.news_repository import NewsRepository
from apps.models.news import News
from apps.utils.model import analyze_sentiment
from apps.utils.scraper import get_news
from collections import defaultdict


class NewsService:
    @staticmethod
    def get_all_news():
        return NewsRepository.find_all()

    @staticmethod
    def get_news(id):
        return NewsRepository.find_by_id(id)

    @staticmethod
    def create_news(data):
        news = News(
            judul=data.get('judul'),
            tanggal=data.get('tanggal'),
            sumber=data.get('sumber'),
            link=data.get('link'),
            meta_title=data.get('meta_title'),
            meta_description=data.get('meta_description'),
            sentimen=data.get('sentimen')
        )
        return NewsRepository.save(news)

    @staticmethod
    def update_news(id, data):

        news = NewsRepository.find_by_id(id)
        if not news:
            return None

        news.judul = data.get('judul', news.judul)
        news.tanggal = data.get('tanggal', news.tanggal)
        news.sumber = data.get('sumber', news.sumber)
        news.link = data.get('link', news.link)
        news.meta_title = data.get('meta_title', news.meta_title)
        news.meta_description = data.get('meta_description', news.meta_description)
        news.sentimen = data.get('sentimen', news.sentimen)
        NewsRepository.save(news)

        return news

    @staticmethod
    def delete_news(id):
        news = NewsRepository.find_by_id(id)
        if not news:
            return False

        NewsRepository.delete(id)
        return True

    @staticmethod
    def scraping_and_analyze(data):
        news_data = get_news(data)
        if not news_data:
            return None

        for news in news_data:
            try:
                news["sentiment"] = analyze_sentiment(news["title"])
                source_name = news["source"]["name"] if isinstance(news["source"], dict) else str(news["source"])
                payload = {
                    'judul' : news.get('title', 'Judul Tidak Tersedia'),
                    'tanggal' : news.get('date', '2025-01-01'), # Default tanggal jika tidak ada
                    'sumber' : source_name,
                    'link' : news.get('link', '#'),
                    'meta_title' : news.get('meta_title', 'Title Tidak Tersedia'),
                    'meta_description' : news.get('meta_description', 'Deskripsi Tidak Tersedia'),
                    'sentimen' : news['sentiment']
                }
                NewsRepository.save(payload)
            except Exception as e:
                print(f"Error saat memproses berita: {e}")

        return news_data

    @staticmethod
    def update_sentiment(id, new_sentiment):
        news = NewsRepository.find_by_id(id)
        if not news:
            return None
        news.sentimen = new_sentiment
        NewsRepository.save(news)
        return news

    @staticmethod
    def search_news(keyword):
        return NewsRepository.find_by_keyword(keyword)

    @staticmethod
    def get_sentimen_summary():
        return NewsRepository.get_sentimen_data()

    @staticmethod
    def get_sentimen_bulanan():
        bulan_map = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        data_berita = NewsRepository.get_sentimen_and_date()
        sentimen_per_bulan = defaultdict(lambda: {"positif": 0, "negatif": 0, "netral": 0})

        for tanggal, sentimen in data_berita:
            # tanggal sudah berupa date object dari SQLAlchemy
            bulan = tanggal.month
            sentimen = sentimen.strip().lower()

            if sentimen == "positif":
                sentimen_per_bulan[bulan]["positif"] += 1
            elif sentimen == "negatif":
                sentimen_per_bulan[bulan]["negatif"] += 1
            else:
                sentimen_per_bulan[bulan]["netral"] += 1

        hasil = []
        for bulan, counts in sentimen_per_bulan.items():
            hasil.append({
                "bulan": bulan_map[bulan],
                "positif": counts["positif"],
                "netral": counts["netral"],
                "negatif": counts["negatif"],
            })

        return hasil

