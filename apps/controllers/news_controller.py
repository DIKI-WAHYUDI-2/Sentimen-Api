import logging

from flask import jsonify, request, send_file
from flask_jwt_extended import verify_jwt_in_request
from flask_restful import Resource, reqparse

from apps.service.news_service import NewsService

logger = logging.getLogger(__name__)


class NewsController(Resource):
    @staticmethod
    def _parse_news_arguments():
        parser = reqparse.RequestParser()
        parser.add_argument("title")
        parser.add_argument("judul")
        parser.add_argument("published_at")
        parser.add_argument("tanggal")
        parser.add_argument("source")
        parser.add_argument("sumber")
        parser.add_argument("url")
        parser.add_argument("link")
        parser.add_argument("content")
        parser.add_argument("isi_berita")
        parser.add_argument("sentiment")
        parser.add_argument("sentimen")
        return parser.parse_args()

    @staticmethod
    def _create_news():
        verify_jwt_in_request()
        payload = NewsController._parse_news_arguments()
        try:
            logger.info("Create news request received")
            news_item = NewsService.create_news(payload)
            if not news_item:
                logger.error("Failed to create news item")
                return {"message": "Failed to create news item"}, 500
            return jsonify(
                {
                    "status": "success",
                    "message": "News item created successfully",
                    "data": news_item.to_dict(),
                }
            )
        except ValueError as exc:
            logger.warning("Create news validation failed", exc_info=True)
            return {"message": str(exc)}, 400

    @staticmethod
    def _get_news():
        verify_jwt_in_request()
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=10, type=int)
        logger.info("Fetching paginated news", extra={"path": request.path, "method": request.method})
        paginated = NewsService.get_paginated_news(page, limit)
        news_items = [item.to_dict() for item in paginated.items]

        return jsonify(
            {
                "message": "News loaded successfully",
                "page": page,
                "limit": limit,
                "total": paginated.total,
                "news": news_items,
            },
            200,
        )

    @staticmethod
    def _update_news(news_id):
        verify_jwt_in_request()
        payload = NewsController._parse_news_arguments()
        try:
            logger.info("Update news request received", extra={"news_id": news_id})
            news_item = NewsService.update_news(news_id, payload)
            if not news_item:
                logger.warning("News item not found during update", extra={"news_id": news_id, "status_code": 404})
                return {"message": "News not found"}, 404
            return jsonify(news_item.to_dict())
        except ValueError as exc:
            logger.warning("Update news validation failed", exc_info=True, extra={"news_id": news_id})
            return {"message": str(exc)}, 400

    @staticmethod
    def _delete_news(news_id):
        verify_jwt_in_request()
        logger.info("Delete news request received", extra={"news_id": news_id})
        if NewsService.delete_news(news_id):
            return {"message": "News deleted successfully"}, 200
        logger.warning("News item not found during delete", extra={"news_id": news_id, "status_code": 404})
        return {"message": "News not found"}, 404

    @staticmethod
    def _search_news():
        verify_jwt_in_request()
        parser = reqparse.RequestParser()
        parser.add_argument("keyword", required=True, help="Keyword is required", location="args")
        args = parser.parse_args()
        logger.info("Searching news by keyword", extra={"query": args["keyword"]})
        results = NewsService.search_news(args["keyword"])
        return {"results": [item.to_dict() for item in results]}, 200

    @staticmethod
    def _get_sentiment_pie():
        verify_jwt_in_request()
        logger.info("Fetching sentiment pie data")
        return {"data": NewsService.get_sentiment_summary()}, 200

    @staticmethod
    def _get_sentiment_trend():
        verify_jwt_in_request()
        year = request.args.get("year", type=int)
        logger.info("Fetching sentiment trend data", extra={"year": year})
        return NewsService.get_monthly_sentiment_summary(year), 200

    @staticmethod
    def _scrape():
        verify_jwt_in_request()
        try:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict) or not payload:
                payload = request.form.to_dict() or request.args.to_dict() or {}

            if not payload:
                logger.warning("Scrape request body is missing", extra={"status_code": 400})
                return {"message": "Request body is required"}, 400

            logger.info("Running scrape pipeline")
            result = NewsService.scrape_classify_and_save(payload)
            return {
                "message": f"Berhasil menyimpan {result['saved_count']} berita baru",
                "count": result["count"],
                "saved_count": result["saved_count"],
                "skipped_count": result["skipped_count"],
                "failed_count": result["failed_count"],
                "data": result["data"],
                "export_file": result.get("export_file"),
            }, 200
        except ValueError as exc:
            logger.warning("Scrape validation failed", exc_info=True)
            return {"message": str(exc)}, 400
        except Exception:
            logger.exception("Failed to run scrape pipeline")
            return {"message": "Internal server error"}, 500

    @staticmethod
    def _export_news():
        verify_jwt_in_request()
        start_month = request.args.get("start_month", "").strip()
        end_month = request.args.get("end_month", "").strip() or None

        if not start_month:
            return {"message": "Parameter start_month wajib diisi"}, 400

        try:
            buf = NewsService.export_news_by_month_range(start_month, end_month)
        except ValueError as exc:
            logger.warning("Export news validation failed", exc_info=True)
            return {"message": str(exc)}, 400
        except FileNotFoundError as exc:
            logger.error("Export template not found", exc_info=True)
            return {"message": str(exc)}, 500
        except Exception:
            logger.exception("Export news failed")
            return {"message": "Internal server error"}, 500

        if end_month and end_month != start_month:
            filename = f"export-berita-{start_month}_sampai_{end_month}.xlsx"
        else:
            filename = f"export-berita-{start_month}.xlsx"

        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    def get(self, news_id=None):
        path = request.path.rstrip("/")

        if path.endswith("/news-search"):
            return self._search_news()
        if path.endswith("/charts/news-sentiment/pie"):
            return self._get_sentiment_pie()
        if path.endswith("/charts/news-sentiment/trend"):
            return self._get_sentiment_trend()
        if path.endswith("/news/export"):
            return self._export_news()

        return self._get_news()

    def post(self, news_id=None):
        path = request.path.rstrip("/")

        if path.endswith("/scrape"):
            return self._scrape()

        return self._create_news()

    def put(self, news_id):
        return self._update_news(news_id)

    def delete(self, news_id):
        return self._delete_news(news_id)
