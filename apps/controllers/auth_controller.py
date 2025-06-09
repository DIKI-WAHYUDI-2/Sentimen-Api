from flask import make_response
from apps.service.user_service import UserService
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, \
    get_jwt_identity
from apps.app import BLACKLIST

class LoginController(Resource):
    @staticmethod
    def post():
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)
        data = parser.parse_args()
        username = data['username']
        password = data['password']
        result = UserService.login(username, password)
        print(result)
        print(username)
        print(password)
        if result['status'] == 'success':
            access_token = result['access_token']
            refresh_token = result['refresh_token']

            response = make_response({
                "status": "success",
                "message": "Login Success"
            }, 200)
            # Gunakan helper JWT
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
        else:
            return {
                "status": "error",
                'message': f"Login Failed: {result['message']}",
            },401

class LogoutController(Resource):
    @jwt_required()
    def post(self):
        jti = get_jwt()['jti']
        BLACKLIST.add(jti)
        response = make_response({
            "status": "success",
            "message": "Logout Success"
        })
        unset_jwt_cookies(response)
        return response

class RefreshTokenController(Resource):
    @staticmethod
    @jwt_required(refresh=True)
    def post():
        result = UserService.refresh_token()
        if result['status'] == 'success':
            access_token = result['access_token']
            response = make_response({
                "status": "success",
                "message": "Refresh Success"
            })
            set_access_cookies(response, access_token)
            return response
        else:
            return {
                "status": "error",
                'message': f"Refresh Failed: {result['message']}",
            }