from flask_restful import Resource, reqparse
from apps.service.news_service import NewsService
from flask import jsonify,request
from flask_jwt_extended import jwt_required
from apps.models.news import News


class NewsController(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('judul', required=True)
        parser.add_argument('tanggal', required=True)
        parser.add_argument('sumber', required=True)
        parser.add_argument('link', required=True)
        parser.add_argument('meta_title')
        parser.add_argument('meta_description')
        parser.add_argument('sentimen', required=True)
        data = parser.parse_args()
        news = NewsService.create_news(data)
        return jsonify(news.to_dict())

    @jwt_required()
    def get(self, news_id=None):
        if news_id:
            news = NewsService.get_news(news_id)
            if news:
                return jsonify(news.to_dict())
            return {"message": "News not found"}, 404
        else:
            page = request.args.get('page', default=1, type=int)
            limit = request.args.get('limit', default=10, type=int)
            news_query = News.query
            paginated = news_query.paginate(page=page, per_page=limit, error_out=False)
            news_list = [n.to_dict() for n in paginated.items]

            return jsonify({
                "page": page,
                "limit": limit,
                "total": paginated.total,
                "news": news_list
            },200)

    @jwt_required()
    def put(self, news_id):
        parser = reqparse.RequestParser()
        parser.add_argument('judul')
        parser.add_argument('tanggal')
        parser.add_argument('sumber')
        parser.add_argument('link')
        parser.add_argument('meta_title')
        parser.add_argument('meta_description')
        parser.add_argument('sentimen')
        data = parser.parse_args()

        news = NewsService.update_news(news_id, data)
        if not news:
            return {"message": "News not found"}, 404
        return jsonify(news.to_dict())

    @jwt_required()
    def delete(self, news_id):
        success = NewsService.delete_news(news_id)
        if success:
            return {"message": "News deleted successfully"}, 200
        return {"message": "News not found"}, 404

class NewsSearchController(Resource):
    @jwt_required()
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('keyword', required=True, help='Keyword harus diisi', location='args')
        data = parser.parse_args()
        keywords = data['keyword']
        results = NewsService.search_news(keywords)
        return {"results": [r.to_dict() for r in results]}, 200

class NewsPieChartSentimenController(Resource):
    @jwt_required()
    def get(self):
        data = NewsService.get_sentimen_summary()
        return {"data": data}, 200

class NewsSentimenTrendChartController(Resource):
    @jwt_required()
    def get(self):
        data = NewsService.get_sentimen_bulanan()
        return {"data": data}, 200

class SentimenLabelUpdateController(Resource):
    @jwt_required()
    def post(self, news_id=None):
        parser = reqparse.RequestParser()
        parser.add_argument('id', required=True, help='ID harus diisi')
        parser.add_argument('sentimen', type=str, required=True, help='Sentimen harus diisi')
        data = parser.parse_args()
        sentimen = NewsService.update_sentiment(data)
        if sentimen:
            return {"message": "Sentimen berhasil diperbarui"}, 200
        return {"message": "Berita tidak ditemukan"}, 404

class ScrapeNewsController(Resource):
    @jwt_required()
    def post(self):
        data = request.json
        result = NewsService.scraping_and_analyze(data)
        if result:
            return {"message": "Berhasil scraping dan analisis", "data": result}, 200
        return {"message": "Gagal melakukan scraping"}, 500