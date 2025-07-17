from flask import request, abort, jsonify
import jwt
import datetime
from sqlalchemy.orm import Session
from models import User
import config

def verify_token():
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

def verify_admin(user_id, session):
    """Admin yetkisi kontrolü"""
    admin_user = session.query(User).filter_by(id=user_id).first()
    
    if not admin_user or not admin_user.is_admin:
        session.close()
        abort(403, description="Forbidden: Admin privileges required")
    
    return admin_user

def verify_active_user(user_id, session):
    """Aktif kullanıcı kontrolü"""
    user = session.query(User).filter_by(id=user_id).first()
    
    if not user or not user.is_active:
        session.close()
        abort(403, description="Forbidden: Inactive user or user not found")
    
    return user

def generate_jwt_token(user_id):
    """JWT token oluşturma"""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=config.JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM) 