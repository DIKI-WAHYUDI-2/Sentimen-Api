import logging

from flask import request
from flask_jwt_extended import verify_jwt_in_request
from flask_restful import Resource

from apps.utils.indobert_inference import analyze_sentiment

logger = logging.getLogger(__name__)


class AnalyzeController(Resource):
    def post(self):
        verify_jwt_in_request()

        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        content = (payload.get("content") or "").strip() or None

        if not title:
            logger.warning("Analyze request missing title")
            return {"status": "error", "message": "title wajib diisi"}, 400

        try:
            sentiment = analyze_sentiment(title, content)
            logger.info("Sentiment analyzed", extra={"title": title[:60], "sentiment": sentiment})
            return {"status": "success", "sentiment": sentiment}, 200
        except Exception:
            logger.exception("Failed to analyze sentiment")
            return {"status": "error", "message": "Gagal menganalisis sentimen"}, 500
