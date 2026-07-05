from apps.repositories.users_repository import UserRepository
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity

class UserService:

    @staticmethod
    def login(username, password):
        user = UserRepository.find_by_username(username)
        if not user:
            return {
                "status": "error",
                "message": "User not found"
            }
        if not UserRepository.verify_password(password, user.password):
            return {
                "status": "error",
                "message": "Incorrect password"
            }
        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=user.username, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user.username, additional_claims=additional_claims)
        return {
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user.role
        }

    @staticmethod
    def refresh_token():
        current_user = get_jwt_identity()
        if not current_user:
            return {
                "status": "error",
                "message": "Invalid user"
            }
        new_access_token = create_access_token(identity=current_user)
        return {
            "status": "success",
            "access_token": new_access_token
        }




