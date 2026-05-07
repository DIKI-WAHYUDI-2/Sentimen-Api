import bcrypt
import logging

from apps.app import db
from apps.models.user import User

logger = logging.getLogger(__name__)

class UserRepository:

    @staticmethod
    def find_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def verify_password(input_password, stored_hash):
        return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash.encode('utf-8'))

    @staticmethod
    def find_by_id(id):
        return User.query.get(id)

    @staticmethod
    def find_all():
        return User.query.all()

    @staticmethod
    def save(data):
        user = User(
            username=data.get('username'),
            password=data.get('password')
        )
        try:
            db.session.add(user)
            db.session.commit()
            logger.debug("User saved successfully")
            return user
        except Exception:
            db.session.rollback()
            logger.exception("Failed to save user")
            raise

    @staticmethod
    def update(id, data):
        user = User.query.get(id)
        if not user:
            return None

        user.username = data.get('username', user.username)
        user.password = data.get('password', user.password)

        try:
            db.session.commit()
            logger.debug("User updated successfully", extra={"user_id": id})
            return user
        except Exception:
            db.session.rollback()
            logger.exception("Failed to update user", extra={"user_id": id})
            raise

    @staticmethod
    def delete_by_username(username):
        user = User.query.filter_by(username=username).first()
        if not user:
            return None

        try:
            db.session.delete(user)
            db.session.commit()
            logger.debug("User deleted successfully")
            return user
        except Exception:
            db.session.rollback()
            logger.exception("Failed to delete user")
            raise

