import os
from flask import Flask, request, abort, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User
import config
from auth import AuthService
from cdn_service import CDNService

app = Flask(__name__)

# PostgreSQL bağlantısı
engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Servis sınıflarını oluştur
auth_service = AuthService(Session)
cdn_service = CDNService(Session, auth_service)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    
    return auth_service.register(username, email, password)

@app.route("/auth", methods=["POST"])
def authenticate():
    data = request.json
    login = data.get("login")  # username veya email
    password = data.get("password")
    
    return auth_service.authenticate(login, password)

@app.route("/reset-api-key", methods=["POST"])
def reset_api_key():
    return auth_service.reset_api_key()

@app.route("/cdn/<path:filename>")
def serve_file(filename):
    return cdn_service.serve_file(filename)

@app.route("/list_all", methods=["GET"])
def list_all():
    return cdn_service.list_all()

@app.route("/list_collection/<collection_name>", methods=["GET"])
def list_collection(collection_name):
    return cdn_service.list_collection(collection_name)

@app.route("/list_collections", methods=["GET"])
def list_collections():
    return cdn_service.list_collections()

@app.route("/admin/users", methods=["GET"])
def list_users():
    return auth_service.list_users()

@app.route("/file_upload", methods=["POST"])
def file_upload():
    return cdn_service.file_upload()

@app.route("/bulk_upload", methods=["POST"])
def bulk_upload():
    return cdn_service.bulk_upload()

@app.route("/delete_file", methods=["POST"])
def delete_file_endpoint():
    return cdn_service.delete_file()

@app.route("/delete_collection", methods=["POST"])
def delete_collection_endpoint():
    return cdn_service.delete_collection()

@app.route("/update_collection", methods=["POST"])
def update_collection_endpoint():
    return cdn_service.update_collection()

@app.route("/create_collection", methods=["POST"])
def create_collection_endpoint():
    return cdn_service.create_collection()

@app.route("/admin/stats", methods=["GET"])
def get_admin_stats():
    return cdn_service.get_admin_stats()

@app.route("/admin/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    return auth_service.update_user(user_id, request.json)

@app.route("/admin/create_admin", methods=["POST"])
def create_admin():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    admin_key = data.get("admin_key")
    
    return auth_service.create_admin(username, email, password, admin_key)

@app.route("/admin/sync_cdn_db", methods=["POST"])
def sync_cdn_db():
    return cdn_service.sync_cdn_db()

if __name__ == "__main__":
    # Docker içinde çalışırken tüm arayüzlerden gelen istekleri dinle
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)


