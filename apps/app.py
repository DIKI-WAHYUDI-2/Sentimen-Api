from datetime import timedelta
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_restful import Api
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
import os

db = SQLAlchemy()
BLACKLIST = set()
# Custom Api class to handle JWT and other errors properly
class CustomApi(Api):
    def handle_error(self, e):
        if isinstance(e, NoAuthorizationError):
            return jsonify({
                "status": "error",
                "message": "Unauthorized: missing or invalid token",
                "detail": str(e)
            }), 401
        elif isinstance(e, HTTPException):
            return jsonify({
                "status": "error",
                "message": e.description
            }), e.code
        else:
            return jsonify({
                "status": "error",
                "message": "Internal Server Error",
                "detail": str(e)  #
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
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
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

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return jti in BLACKLIST

    # Import controllers
    from apps.controllers.news_controller import (
        NewsController,
        NewsSearchController,
        NewsPieChartSentimenController,
        NewsSentimenTrendChartController,
        SentimenLabelUpdateController,
        ScrapeNewsController,
    )
    from apps.controllers.auth_controller import (
        LoginController,
        LogoutController,
        RefreshTokenController
    )

    # Register routes
    api.add_resource(NewsController, '/news', '/news/<int:news_id>')
    api.add_resource(NewsSentimenTrendChartController, '/charts/news-sentimen/trend')
    api.add_resource(NewsPieChartSentimenController, '/charts/news-sentimen/pie')
    api.add_resource(SentimenLabelUpdateController, '/sentiment/update-label')
    api.add_resource(NewsSearchController, '/news-search')
    api.add_resource(ScrapeNewsController, '/scrape/news')
    api.add_resource(LoginController, '/auth/login')
    api.add_resource(RefreshTokenController, '/auth/refresh-token')
    api.add_resource(LogoutController, '/auth/logout')

    return app
