import jwt
import datetime
from flask import request, abort, jsonify
from sqlalchemy.orm import Session
from models import User
import config

class AuthService:
    def __init__(self, session_maker):
        self.Session = session_maker

    def verify_token(self):
        """JWT token doğrulama işlevi"""
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
        try:
            decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
            return decoded_token
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")

    def verify_admin(self, user_id):
        """Admin yetkisi kontrolü"""
        session = self.Session()
        try:
            admin_user = session.query(User).filter_by(id=user_id).first()
            
            if not admin_user or not admin_user.is_admin:
                abort(403, description="Forbidden: Admin privileges required")
            
            return admin_user
        finally:
            session.close()

    def verify_active_user(self, user_id):
        """Aktif kullanıcı kontrolü"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user or not user.is_active:
                abort(403, description="Forbidden: Inactive user or user not found")
            
            return user
        finally:
            session.close()

    def generate_jwt_token(self, user_id):
        """JWT token oluşturma"""
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=config.JWT_EXPIRATION_DAYS)
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

    def register(self, username, email, password):
        """Kullanıcı kaydı oluşturma"""
        if not username or not email or not password:
            return jsonify({"message": "Username, email and password are required"}), 400
        
        session = self.Session()
        try:
            existing_user = session.query(User).filter((User.username == username) | (User.email == email)).first()
            
            if existing_user:
                if existing_user.username == username:
                    return jsonify({"message": "This username is already in use"}), 400
                else:
                    return jsonify({"message": "This email is already in use"}), 400
            
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            
            session.add(new_user)
            session.commit()
            
            token = self.generate_jwt_token(new_user.id)
            
            result = {
                "token": token,
                "api_key": new_user.api_key,
                "user_id": new_user.id
            }
            
            return jsonify(result), 201
        finally:
            session.close()

    def authenticate(self, login, password):
        """Kullanıcı girişi (username veya email ile)"""
        if not login or not password:
            return jsonify({"message": "Login and password are required"}), 400
        
        session = self.Session()
        try:
            # Username veya email ile kullanıcıyı bul
            user = session.query(User).filter(
                (User.username == login) | (User.email == login)
            ).first()
            
            if not user or not user.check_password(password):
                return jsonify({"message": "Invalid username/email or password"}), 401
            
            if not user.is_active:
                return jsonify({"message": "Account is disabled"}), 403
            
            token = self.generate_jwt_token(user.id)
            
            result = {
                "token": token,
                "api_key": user.api_key,
                "user_id": user.id
            }
            
            return jsonify(result), 200
        finally:
            session.close()

    def reset_api_key(self):
        """Kullanıcının API anahtarını sıfırlama"""
        decoded_token = self.verify_token()
        user_id = decoded_token.get("user_id")
        
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({"message": "User not found"}), 404
            
            new_api_key = user.generate_api_key()
            session.commit()
            
            result = {"api_key": new_api_key}
            return jsonify(result), 200
        finally:
            session.close()

    def create_admin(self, username, email, password, admin_key):
        """İlk admin kullanıcısını oluşturma"""
        # Bu ilk admin oluşturma için güvenlik anahtarı kontrolü
        if admin_key != "wallify_initial_setup_key":
            return jsonify({"message": "Invalid admin key"}), 403
        
        if not username or not email or not password:
            return jsonify({"message": "Username, email and password are required"}), 400
        
        session = self.Session()
        try:
            existing_user = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    return jsonify({"message": "This username is already in use"}), 400
                else:
                    return jsonify({"message": "This email is already in use"}), 400
            
            new_admin = User(username=username, email=email, is_admin=True)
            new_admin.set_password(password)
            
            session.add(new_admin)
            session.commit()
            
            token = self.generate_jwt_token(new_admin.id)
            
            result = {
                "token": token,
                "api_key": new_admin.api_key,
                "user_id": new_admin.id,
                "is_admin": True
            }
            
            return jsonify(result), 201
        finally:
            session.close()

    def update_user(self, user_id, data):
        """Kullanıcı bilgilerini güncelleme (admin yetkisi gerekli)"""
        decoded_token = self.verify_token()
        admin_id = decoded_token.get("user_id")
        
        if not admin_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Admin kontrolü
        self.verify_admin(admin_id)
        
        is_active = data.get("is_active")
        is_admin = data.get("is_admin")
        
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({"message": "Kullanıcı bulunamadı"}), 404
            
            if is_active is not None:
                user.is_active = is_active
            
            if is_admin is not None:
                user.is_admin = is_admin
            
            session.commit()
            result = user.to_dict()
            
            return jsonify(result), 200
        finally:
            session.close()

    def list_users(self):
        """Tüm kullanıcıları listele (admin yetkisi gerekli)"""
        decoded_token = self.verify_token()
        user_id = decoded_token.get("user_id")
        
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Admin kontrolü
        self.verify_admin(user_id)
        
        session = self.Session()
        try:
            users = session.query(User).all()
            result = [user.to_dict() for user in users]
            
            return jsonify({"users": result}), 200
        finally:
            session.close() 



