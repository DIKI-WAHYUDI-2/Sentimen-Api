import logging

from flask import make_response
from flask_restful import Resource, reqparse
from flask_jwt_extended import get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request

from apps.app import BLACKLIST
from apps.service.user_service import UserService

logger = logging.getLogger(__name__)

class AuthController(Resource):
    @staticmethod
    def _login():
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)
        data = parser.parse_args()
        username = data['username']
        password = data['password']
        logger.info("Login attempt received")
        result = UserService.login(username, password)
        if result['status'] == 'success':
            access_token = result['access_token']
            refresh_token = result['refresh_token']
            logger.info("Login succeeded")

            response = make_response({
                "status": "success",
                "message": "Login Success"
            }, 200)
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
        else:
            logger.warning("Login failed", extra={"status_code": 401})
            return {
                "status": "error",
                'message': f"Username atau Password Salah",
            },401

    @staticmethod
    def _logout():
        verify_jwt_in_request()
        jti = get_jwt()['jti']
        BLACKLIST.add(jti)
        logger.info("Logout succeeded")
        response = make_response({
            "status": "success",
            "message": "Logout Success"
        })
        unset_jwt_cookies(response)
        return response

    @staticmethod
    def _refresh_token():
        verify_jwt_in_request(refresh=True)
        result = UserService.refresh_token()
        if result['status'] == 'success':
            access_token = result['access_token']
            logger.info("Access token refreshed successfully")
            response = make_response({
                "status": "success",
                "message": "Refresh Success"
            })
            set_access_cookies(response, access_token)
            return response
        else:
            logger.warning("Refresh token failed")
            return {
                "status": "error",
                'message': f"Refresh Failed: {result['message']}",
            }

    def post(self, action):
        if action == 'login':
            return self._login()
        if action == 'logout':
            return self._logout()
        if action == 'refresh-token':
            return self._refresh_token()

        logger.warning("Unknown auth endpoint requested", extra={"path": action, "status_code": 404})
        return {
            "status": "error",
            "message": "Auth endpoint not found"
        }, 404
