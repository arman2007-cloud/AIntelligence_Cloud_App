# models.py
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.role = user_dict['role']
        
    def get_id(self):
        """
        🛡️ FIX MULTI-TENANT: 
        Fuerza a Flask-Login a usar el ID real de la base de datos como identificador único 
        de sesión, evitando que las identidades se mezclen o se pierdan en la cookie.
        """
        return str(self.id)