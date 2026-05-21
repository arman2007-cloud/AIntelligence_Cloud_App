# models.py
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.role = user_dict['role']