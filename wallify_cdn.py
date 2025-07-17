import os
from flask import Flask, send_file, request, abort, jsonify
from PIL import Image
from io import BytesIO
import datetime
from natsort import natsorted
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import jwt

from models import Base, User
import config
from auth import verify_token, verify_admin, verify_active_user, generate_jwt_token

app = Flask(__name__)

# PostgreSQL bağlantısı
engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

cdn_folder = config.CDN_FOLDER


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    
    session = Session()
    existing_user = session.query(User).filter_by(username=username).first()
    
    if existing_user:
        session.close()
        return jsonify({"message": "This username is already in use"}), 400
    
    new_user = User(username=username)
    new_user.set_password(password)
    
    session.add(new_user)
    session.commit()
    
    token = generate_jwt_token(new_user.id)
    
    result = {
        "token": token,
        "api_key": new_user.api_key,
        "user_id": new_user.id
    }
    
    session.close()
    return jsonify(result), 201

@app.route("/auth", methods=["POST"])
def authenticate():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        session.close()
        return jsonify({"message": "Invalid username or password"}), 401
    
    if not user.is_active:
        session.close()
        return jsonify({"message": "Account is disabled"}), 403
    
    token = generate_jwt_token(user.id)
    
    result = {
        "token": token,
        "api_key": user.api_key,
        "user_id": user.id
    }
    
    session.close()
    return jsonify(result), 200

@app.route("/reset-api-key", methods=["POST"])
def reset_api_key():
    decoded_token = verify_token()
    user_id = decoded_token.get("user_id")
    
    if not user_id:
        abort(403, description="Forbidden: Invalid token payload")
    
    session = Session()
    user = session.query(User).filter_by(id=user_id).first()
    
    if not user:
        session.close()
        return jsonify({"message": "User not found"}), 404
    
    new_api_key = user.generate_api_key()
    session.commit()
    
    result = {"api_key": new_api_key}
    session.close()
    
    return jsonify(result), 200

@app.route("/cdn/<path:filename>")
def serve_file(filename):
    token = request.args.get("token")
    if not token:
        # Header'dan token'ı kontrol et (geriye dönük uyumluluk için)
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()

        width = request.args.get("width", type=int)
        file_path = os.path.join(cdn_folder, filename)
        if not os.path.exists(file_path):
            return abort(404)
        if width:
            image = Image.open(file_path)
            aspect_ratio = image.width / image.height
            new_height = int(width / aspect_ratio)
            resized_image = image.resize((width, new_height))
            image_io = BytesIO()
            resized_image.save(image_io, format=image.format)
            image_io.seek(0)
            return send_file(image_io, mimetype=f"image/{image.format.lower()}")
        return send_file(file_path)
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")

@app.route("/list_all", methods=["GET"])
def list_all():
    token = request.args.get("token")
    if not token:
        # Header'dan token'ı kontrol et (geriye dönük uyumluluk için)
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        base_url = request.host_url.rstrip("/")
        files = []
        for root, dirs, filenames in os.walk(cdn_folder):
            for filename in filenames:
                file_path = os.path.relpath(os.path.join(root, filename), cdn_folder)
                file_path = file_path.replace("\\", "/")
                if os.path.dirname(file_path):
                    files.append(f"{base_url}/cdn/{file_path}")
                else:
                    files.append(f"{base_url}/cdn/{filename}")
        files = natsorted(files)

        start = (page - 1) * per_page
        end = start + per_page
        paginated_files = files[start:end]

        return jsonify(
            {
                "page": page,
                "per_page": per_page,
                "total": len(files),
                "files": paginated_files,
            }
        )
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")

@app.route("/list_collection/<collection_name>", methods=["GET"])
def list_collection(collection_name):
    token = request.args.get("token")
    if not token:
        # Header'dan token'ı kontrol et (geriye dönük uyumluluk için)
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()

        collection_path = os.path.join(cdn_folder, collection_name)
        if not os.path.exists(collection_path) or not os.path.isdir(collection_path):
            abort(404, description="Collection not found")

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        base_url = request.host_url.rstrip("/")
        files = [
            f"{base_url}/cdn/{collection_name}/{f}".replace("\\", "/")
            for f in os.listdir(collection_path)
        ]
        files = natsorted(files)

        start = (page - 1) * per_page
        end = start + per_page
        paginated_files = files[start:end]

        return jsonify(
            {
                "page": page,
                "per_page": per_page,
                "total": len(files),
                "files": paginated_files,
            }
        )
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")

@app.route("/list_collections", methods=["GET"])
def list_collections():
    token = request.args.get("token")
    if not token:
        # Header'dan token'ı kontrol et (geriye dönük uyumluluk için)
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()

        collections = [
            f"{d}"
            for d in os.listdir(cdn_folder)
            if os.path.isdir(os.path.join(cdn_folder, d))
        ]
        collections = natsorted(collections)

        return jsonify({"total": len(collections), "collections": collections})
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")

@app.route("/admin/users", methods=["GET"])
def list_users():
    decoded_token = verify_token()
    user_id = decoded_token.get("user_id")
    
    if not user_id:
        abort(403, description="Forbidden: Invalid token payload")
    
    # Admin kontrolü
    session = Session()
    verify_admin(user_id, session)
    
    users = session.query(User).all()
    result = [user.to_dict() for user in users]
    
    session.close()
    return jsonify({"users": result})

@app.route("/file_upload", methods=["POST"])
def file_upload():
    # Token kontrolü
    token = request.args.get("token")
    if not token:
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()
        
        # Dosya kontrolü
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "No selected file"}), 400
        
        # Koleksiyon adı
        collection = request.form.get('collection')
        
        # Dosya kaydetme işlemi
        if collection:
            target_dir = os.path.join(cdn_folder, collection)
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = cdn_folder
        
        file_path = os.path.join(target_dir, file.filename)
        
        # Dosya adı çakışması kontrolü
        if os.path.exists(file_path):
            name, ext = os.path.splitext(file.filename)
            counter = 1
            while os.path.exists(file_path):
                new_name = f"{name}_{counter}{ext}"
                file_path = os.path.join(target_dir, new_name)
                counter += 1
        
        # Dosyayı kaydet
        file.save(file_path)
        
        # Dosya bilgilerini döndür
        rel_path = os.path.relpath(file_path, cdn_folder).replace("\\", "/")
        file_info = {
            "success": True,
            "path": rel_path,
            "name": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "url": f"{request.host_url.rstrip('/')}/cdn/{rel_path}"
        }
        
        return jsonify(file_info), 201
        
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/bulk_upload", methods=["POST"])
def bulk_upload():
    # Token kontrolü
    token = request.args.get("token")
    if not token:
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()
        
        # Dosya kontrolü
        if 'files[]' not in request.files:
            return jsonify({"success": False, "message": "No files part"}), 400
        
        files = request.files.getlist('files[]')
        if len(files) == 0:
            return jsonify({"success": False, "message": "No selected files"}), 400
        
        # Koleksiyon adı
        collection = request.form.get('collection')
        
        # Sonuçları tutacak liste
        results = []
        
        # Her dosya için işlem yap
        for file in files:
            if file.filename == '':
                continue
                
            # Dosya kaydetme işlemi
            if collection:
                target_dir = os.path.join(cdn_folder, collection)
                os.makedirs(target_dir, exist_ok=True)
            else:
                target_dir = cdn_folder
            
            file_path = os.path.join(target_dir, file.filename)
            
            # Dosya adı çakışması kontrolü
            if os.path.exists(file_path):
                name, ext = os.path.splitext(file.filename)
                counter = 1
                while os.path.exists(file_path):
                    new_name = f"{name}_{counter}{ext}"
                    file_path = os.path.join(target_dir, new_name)
                    counter += 1
            
            # Dosyayı kaydet
            try:
                file.save(file_path)
                
                # Dosya bilgilerini ekle
                rel_path = os.path.relpath(file_path, cdn_folder).replace("\\", "/")
                file_info = {
                    "success": True,
                    "path": rel_path,
                    "name": os.path.basename(file_path),
                    "size": os.path.getsize(file_path),
                    "url": f"{request.host_url.rstrip('/')}/cdn/{rel_path}"
                }
                results.append(file_info)
            except Exception as e:
                results.append({
                    "success": False,
                    "name": file.filename,
                    "message": str(e)
                })
        
        return jsonify({
            "success": True,
            "total": len(files),
            "successful": len([r for r in results if r.get("success", False)]),
            "failed": len([r for r in results if not r.get("success", False)]),
            "results": results
        }), 201
        
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/delete_file", methods=["POST"])
def delete_file_endpoint():
    # Token kontrolü
    token = request.args.get("token")
    if not token:
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()
        
        # Dosya yolu kontrolü
        data = request.json
        if not data or 'path' not in data:
            return jsonify({"success": False, "message": "File path is required"}), 400
        
        file_path = data['path']
        
        # Güvenlik kontrolü - path traversal saldırılarına karşı
        normalized_path = os.path.normpath(file_path)
        if normalized_path.startswith('..'):
            return jsonify({"success": False, "message": "Invalid file path"}), 400
        
        # Tam dosya yolu
        full_path = os.path.join(cdn_folder, normalized_path)
        
        # Dosya var mı kontrol et
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return jsonify({"success": False, "message": "File not found"}), 404
        
        # Dosyayı sil
        os.remove(full_path)
        
        return jsonify({"success": True, "message": "File deleted successfully"}), 200
        
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/delete_collection", methods=["POST"])
def delete_collection_endpoint():
    # Token kontrolü
    token = request.args.get("token")
    if not token:
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()
        
        # Koleksiyon adı kontrolü
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"success": False, "message": "Collection name is required"}), 400
        
        collection_name = data['name']
        
        # Güvenlik kontrolü - path traversal saldırılarına karşı
        normalized_name = os.path.normpath(collection_name)
        if normalized_name.startswith('..') or '/' in normalized_name or '\\' in normalized_name:
            return jsonify({"success": False, "message": "Invalid collection name"}), 400
        
        # Tam klasör yolu
        collection_path = os.path.join(cdn_folder, normalized_name)
        
        # Klasör var mı kontrol et
        if not os.path.exists(collection_path) or not os.path.isdir(collection_path):
            return jsonify({"success": False, "message": "Collection not found"}), 404
        
        # Klasörü sil (içindeki tüm dosyalarla birlikte)
        import shutil
        shutil.rmtree(collection_path)
        
        return jsonify({"success": True, "message": "Collection deleted successfully"}), 200
        
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/update_collection", methods=["POST"])
def update_collection_endpoint():
    # Token kontrolü
    token = request.args.get("token")
    if not token:
        token = request.headers.get("Authorization")
        if not token:
            abort(403, description="Forbidden: Missing token")
    
    try:
        decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = decoded_token.get("user_id")
        if not user_id:
            abort(403, description="Forbidden: Invalid token payload")
        
        # Kullanıcının aktif olup olmadığını kontrol et
        session = Session()
        verify_active_user(user_id, session)
        session.close()
        
        # Koleksiyon bilgileri kontrolü
        data = request.json
        if not data or 'old_name' not in data or 'new_name' not in data:
            return jsonify({"success": False, "message": "Old and new collection names are required"}), 400
        
        old_name = data['old_name']
        new_name = data['new_name']
        
        # Güvenlik kontrolü - path traversal saldırılarına karşı
        normalized_old_name = os.path.normpath(old_name)
        normalized_new_name = os.path.normpath(new_name)
        if normalized_old_name.startswith('..') or '/' in normalized_old_name or '\\' in normalized_old_name:
            return jsonify({"success": False, "message": "Invalid old collection name"}), 400
        if normalized_new_name.startswith('..') or '/' in normalized_new_name or '\\' in normalized_new_name:
            return jsonify({"success": False, "message": "Invalid new collection name"}), 400
        
        # Tam klasör yolları
        old_path = os.path.join(cdn_folder, normalized_old_name)
        new_path = os.path.join(cdn_folder, normalized_new_name)
        
        # Eski klasör var mı kontrol et
        if not os.path.exists(old_path) or not os.path.isdir(old_path):
            return jsonify({"success": False, "message": "Collection not found"}), 404
        
        # Yeni isimde klasör var mı kontrol et
        if os.path.exists(new_path):
            return jsonify({"success": False, "message": "A collection with this name already exists"}), 400
        
        # Klasörü yeniden adlandır
        os.rename(old_path, new_path)
        
        return jsonify({
            "success": True, 
            "message": "Collection updated successfully",
            "old_name": old_name,
            "new_name": new_name
        }), 200
        
    except jwt.ExpiredSignatureError:
        abort(403, description="Forbidden: Token has expired")
    except jwt.InvalidTokenError:
        abort(403, description="Forbidden: Invalid token")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/admin/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    decoded_token = verify_token()
    admin_id = decoded_token.get("user_id")
    
    if not admin_id:
        abort(403, description="Forbidden: Invalid token payload")
    
    # Admin kontrolü
    session = Session()
    verify_admin(admin_id, session)
    
    data = request.json
    is_active = data.get("is_active")
    is_admin = data.get("is_admin")
    
    user = session.query(User).filter_by(id=user_id).first()
    
    if not user:
        session.close()
        return jsonify({"message": "Kullanıcı bulunamadı"}), 404
    
    if is_active is not None:
        user.is_active = is_active
    
    if is_admin is not None:
        user.is_admin = is_admin
    
    session.commit()
    result = user.to_dict()
    
    session.close()
    return jsonify(result)

@app.route("/admin/create_admin", methods=["POST"])
def create_admin():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    admin_key = data.get("admin_key")
    
    # Bu ilk admin oluşturma için güvenlik anahtarı kontrolü
    # Gerçek bir uygulamada daha güvenli bir yöntem kullanılmalı
    if admin_key != "wallify_initial_setup_key":
        return jsonify({"message": "Invalid admin key"}), 403
    
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    
    session = Session()
    existing_user = session.query(User).filter_by(username=username).first()
    
    if existing_user:
        session.close()
        return jsonify({"message": "This username is already in use"}), 400
    
    new_admin = User(username=username, is_admin=True)
    new_admin.set_password(password)
    
    session.add(new_admin)
    session.commit()
    
    token = generate_jwt_token(new_admin.id)
    
    result = {
        "token": token,
        "api_key": new_admin.api_key,
        "user_id": new_admin.id,
        "is_admin": True
    }
    
    session.close()
    return jsonify(result), 201

if __name__ == "__main__":
    # Docker içinde çalışırken tüm arayüzlerden gelen istekleri dinle
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
