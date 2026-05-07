from datetime import timedelta
import time
import uuid

from flask import Flask, jsonify
from flask import g, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_restful import Api
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import os

from apps.logging_config import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

db = SQLAlchemy()
BLACKLIST = set()


class CustomApi(Api):
    def handle_error(self, e):
        if isinstance(e, NoAuthorizationError):
            logger.warning("Authorization failed", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "Unauthorized: missing or invalid token",
                "detail": str(e)
            }), 401
        elif isinstance(e, HTTPException):
            logger.warning("HTTP exception raised", extra={"status_code": e.code})
            return jsonify({
                "status": "error",
                "message": e.description
            }), e.code
        else:
            logger.exception("Unhandled application error")
            return jsonify({
                "status": "error",
                "message": "Internal Server Error",
                "detail": str(e)
            }), 500

def create_app():
    HOST = str(os.environ.get('DB_HOST'))
    DATABASE = str(os.environ.get('DB_NAME'))
    USERNAME = str(os.environ.get('DB_USERNAME'))
    PASSWORD = str(os.environ.get('DB_PASSWORD'))
    JWT_SECRET = str(os.environ.get('JWT_SECRET'))

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = JWT_SECRET
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=24)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=24)
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    app.config['JWT_TOKEN_LOCATION'] = ['cookies','headers']
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/auth/refresh-token'
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
    app.config['JWT_REFRESH_COOKIE_NAME'] = 'refresh_token'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False

    db.init_app(app)
    jwt = JWTManager(app)
    api = CustomApi(app)
    CORS(app, resources={
         r"/*": {
             "origins": ["http://localhost:3000"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }
    })

    @app.before_request
    def start_request_logging():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.request_started_at = time.perf_counter()
        logger.info(
            "Request started",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
            },
        )

    @app.after_request
    def log_response(response):
        duration_ms = None
        if hasattr(g, "request_started_at"):
            duration_ms = round((time.perf_counter() - g.request_started_at) * 1000, 2)

        logger.info(
            "Request completed",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
            },
        )
        if duration_ms is not None:
            logger.debug(
                f"Request duration: {duration_ms} ms",
                extra={
                    "request_id": getattr(g, "request_id", None),
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                },
            )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return jti in BLACKLIST

    from apps.controllers.news_controller import NewsController
    from apps.controllers.auth_controller import AuthController
    from apps.controllers.analyze_controller import AnalyzeController

    api.add_resource(
        NewsController,
        '/news',
        '/news/export',
        '/news/<int:news_id>',
        '/charts/news-sentiment/trend',
        '/charts/news-sentiment/pie',
        '/news-search',
        '/scrape'
    )
    api.add_resource(AuthController, '/auth/<string:action>')
    api.add_resource(AnalyzeController, '/news/analyze')

    logger.info("Application created successfully")

    return app
