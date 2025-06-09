from apps.models.user import User
import bcrypt
from apps.app import db

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
        user = User(data)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(id, data):
        user = User.query.get(id)
        user.update(data)
        db.session.commit()
        return user

    @staticmethod
    def delete_by_username(username):
        user = User.query.filter_by(username=username).first()
        db.session.delete(user)
        db.session.commit()
        return user

