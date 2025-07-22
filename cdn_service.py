import os
from flask import send_file, request, abort, jsonify
from PIL import Image
from io import BytesIO
import jwt
from natsort import natsorted
import mimetypes
import config
from models import File, Collection

class CDNService:
    def __init__(self, session_maker, auth_service):
        self.Session = session_maker
        self.auth_service = auth_service
        self.cdn_folder = config.CDN_FOLDER
    
    def serve_file(self, filename):
        """Dosya servis etme"""
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
            self.auth_service.verify_active_user(user_id)

            width = request.args.get("width", type=int)
            file_path = os.path.join(self.cdn_folder, filename)
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
    
    def list_all(self):
        """Tüm dosyaları listeleme"""
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
            self.auth_service.verify_active_user(user_id)

            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)

            # Veritabanından dosyaları çek
            session = self.Session()
            try:
                total = session.query(File).count()
                files = session.query(File).order_by(File.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                base_url = request.host_url.rstrip("/")
                file_list = []
                
                for file in files:
                    file_dict = file.to_dict()
                    file_dict["url"] = f"{base_url}/cdn/{file.file_path}"
                    file_list.append(file_dict)
                
                return jsonify({
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "files": file_list,
                })
            finally:
                session.close()
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
    
    def list_collection(self, collection_name):
        """Koleksiyon içindeki dosyaları listeleme"""
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
            self.auth_service.verify_active_user(user_id)

            # Veritabanından koleksiyon ve dosyaları çek
            session = self.Session()
            try:
                collection = session.query(Collection).filter(Collection.name == collection_name).first()
                if not collection:
                    abort(404, description="Collection not found")
                
                page = request.args.get("page", 1, type=int)
                per_page = request.args.get("per_page", 10, type=int)
                
                total = session.query(File).filter(File.collection_id == collection.id).count()
                files = session.query(File).filter(File.collection_id == collection.id).order_by(File.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                base_url = request.host_url.rstrip("/")
                file_list = []
                
                for file in files:
                    file_dict = file.to_dict()
                    file_dict["url"] = f"{base_url}/cdn/{file.file_path}"
                    file_list.append(file_dict)
                
                return jsonify({
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "collection": collection.to_dict(),
                    "files": file_list,
                })
            finally:
                session.close()
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
    
    def list_collections(self):
        """Tüm koleksiyonları listeleme"""
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
            self.auth_service.verify_active_user(user_id)

            # Veritabanından koleksiyonları çek
            session = self.Session()
            try:
                collections = session.query(Collection).order_by(Collection.name).all()
                collection_list = [collection.to_dict() for collection in collections]
                
                return jsonify({
                    "total": len(collection_list),
                    "collections": collection_list
                })
            finally:
                session.close()
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
    
    def file_upload(self):
        """Dosya yükleme (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
            # Dosya kontrolü
            if 'file' not in request.files:
                return jsonify({"success": False, "message": "No file part"}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({"success": False, "message": "No selected file"}), 400
            
            # Koleksiyon adı
            collection_name = request.form.get('collection')
            
            session = self.Session()
            try:
                # Koleksiyon kontrolü
                collection_id = None
                if collection_name:
                    collection = session.query(Collection).filter(Collection.name == collection_name).first()
                    if not collection:
                        # Yeni koleksiyon oluştur
                        collection = Collection(name=collection_name)
                        session.add(collection)
                        session.flush()  # ID almak için flush
                    collection_id = collection.id
                    
                    # Hedef dizini oluştur
                    target_dir = os.path.join(self.cdn_folder, collection_name)
                    os.makedirs(target_dir, exist_ok=True)
                else:
                    target_dir = self.cdn_folder
                
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
                file_size = os.path.getsize(file_path)
                
                # MIME tipini belirle
                mime_type, _ = mimetypes.guess_type(file_path)
                
                # Dosya yolunu veritabanı için düzenle
                rel_path = os.path.relpath(file_path, self.cdn_folder).replace("\\", "/")
                
                # Veritabanına kaydet
                db_file = File(
                    file_name=os.path.basename(file_path),
                    file_path=rel_path,
                    file_size=file_size,
                    mime_type=mime_type,
                    collection_id=collection_id
                )
                session.add(db_file)
                
                # Koleksiyon istatistiklerini güncelle
                if collection_id:
                    collection.update_stats(session)
                
                session.commit()
                
                # Dosya bilgilerini döndür
                file_info = db_file.to_dict()
                file_info["success"] = True
                file_info["url"] = f"{request.host_url.rstrip('/')}/cdn/{rel_path}"
                
                return jsonify(file_info), 201
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def bulk_upload(self):
        """Toplu dosya yükleme (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
            # Dosya kontrolü
            if 'files[]' not in request.files:
                return jsonify({"success": False, "message": "No files part"}), 400
            
            files = request.files.getlist('files[]')
            if len(files) == 0:
                return jsonify({"success": False, "message": "No selected files"}), 400
            
            # Koleksiyon adı
            collection_name = request.form.get('collection')
            
            session = self.Session()
            try:
                # Koleksiyon kontrolü
                collection_id = None
                if collection_name:
                    collection = session.query(Collection).filter(Collection.name == collection_name).first()
                    if not collection:
                        # Yeni koleksiyon oluştur
                        collection = Collection(name=collection_name)
                        session.add(collection)
                        session.flush()  # ID almak için flush
                    collection_id = collection.id
                    
                    # Hedef dizini oluştur
                    target_dir = os.path.join(self.cdn_folder, collection_name)
                    os.makedirs(target_dir, exist_ok=True)
                else:
                    target_dir = self.cdn_folder
                
                # Sonuçları tutacak liste
                results = []
                
                # Her dosya için işlem yap
                for file in files:
                    if file.filename == '':
                        continue
                        
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
                        file_size = os.path.getsize(file_path)
                        
                        # MIME tipini belirle
                        mime_type, _ = mimetypes.guess_type(file_path)
                        
                        # Dosya yolunu veritabanı için düzenle
                        rel_path = os.path.relpath(file_path, self.cdn_folder).replace("\\", "/")
                        
                        # Veritabanına kaydet
                        db_file = File(
                            file_name=os.path.basename(file_path),
                            file_path=rel_path,
                            file_size=file_size,
                            mime_type=mime_type,
                            collection_id=collection_id
                        )
                        session.add(db_file)
                        
                        # Dosya bilgilerini ekle
                        file_info = db_file.to_dict()
                        file_info["success"] = True
                        file_info["url"] = f"{request.host_url.rstrip('/')}/cdn/{rel_path}"
                        results.append(file_info)
                    except Exception as e:
                        results.append({
                            "success": False,
                            "name": file.filename,
                            "message": str(e)
                        })
                
                # Koleksiyon istatistiklerini güncelle
                if collection_id:
                    collection.update_stats(session)
                
                session.commit()
                
                return jsonify({
                    "success": True,
                    "total": len(files),
                    "successful": len([r for r in results if r.get("success", False)]),
                    "failed": len([r for r in results if not r.get("success", False)]),
                    "results": results
                }), 201
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def delete_file(self):
        """Dosya silme (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
            # Dosya yolu kontrolü
            data = request.json
            if not data or 'path' not in data:
                return jsonify({"success": False, "message": "File path is required"}), 400
            
            file_path = data['path']
            
            # Güvenlik kontrolü - path traversal saldırılarına karşı
            normalized_path = os.path.normpath(file_path)
            if normalized_path.startswith('..'):
                return jsonify({"success": False, "message": "Invalid file path"}), 400
            
            session = self.Session()
            try:
                # Veritabanında dosyayı bul
                db_file = session.query(File).filter(File.file_path == file_path).first()
                if not db_file:
                    return jsonify({"success": False, "message": "File not found in database"}), 404
                
                # Koleksiyon ID'sini kaydet
                collection_id = db_file.collection_id
                
                # Tam dosya yolu
                full_path = os.path.join(self.cdn_folder, normalized_path)
                
                # Dosya var mı kontrol et
                if not os.path.exists(full_path) or not os.path.isfile(full_path):
                    # Dosya fiziksel olarak yok ama veritabanında var, sadece veritabanından silelim
                    session.delete(db_file)
                else:
                    # Dosyayı fiziksel olarak sil
                    os.remove(full_path)
                    # Veritabanından da sil
                    session.delete(db_file)
                
                # Koleksiyon istatistiklerini güncelle
                if collection_id:
                    collection = session.query(Collection).filter(Collection.id == collection_id).first()
                    if collection:
                        collection.update_stats(session)
                
                session.commit()
                
                return jsonify({"success": True, "message": "File deleted successfully"}), 200
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def delete_collection(self):
        """Koleksiyon silme (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
            # Koleksiyon adı kontrolü
            data = request.json
            if not data or 'name' not in data:
                return jsonify({"success": False, "message": "Collection name is required"}), 400
            
            collection_name = data['name']
            
            # Güvenlik kontrolü - path traversal saldırılarına karşı
            normalized_name = os.path.normpath(collection_name)
            if normalized_name.startswith('..') or '/' in normalized_name or '\\' in normalized_name:
                return jsonify({"success": False, "message": "Invalid collection name"}), 400
            
            session = self.Session()
            try:
                # Veritabanında koleksiyonu bul
                collection = session.query(Collection).filter(Collection.name == collection_name).first()
                if not collection:
                    return jsonify({"success": False, "message": "Collection not found in database"}), 404
                
                # Tam klasör yolu
                collection_path = os.path.join(self.cdn_folder, normalized_name)
                
                # Klasör var mı kontrol et
                if os.path.exists(collection_path) and os.path.isdir(collection_path):
                    # Klasörü sil (içindeki tüm dosyalarla birlikte)
                    import shutil
                    shutil.rmtree(collection_path)
                
                # Veritabanından koleksiyonu sil (cascade ile ilişkili dosyalar da silinecek)
                session.delete(collection)
                session.commit()
                
                return jsonify({"success": True, "message": "Collection deleted successfully"}), 200
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def update_collection(self):
        """Koleksiyon güncelleme (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
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
            
            session = self.Session()
            try:
                # Veritabanında koleksiyonu bul
                collection = session.query(Collection).filter(Collection.name == old_name).first()
                if not collection:
                    return jsonify({"success": False, "message": "Collection not found in database"}), 404
                
                # Yeni isimde koleksiyon var mı kontrol et
                existing_collection = session.query(Collection).filter(Collection.name == new_name).first()
                if existing_collection:
                    return jsonify({"success": False, "message": "A collection with this name already exists in database"}), 400
                
                # Tam klasör yolları
                old_path = os.path.join(self.cdn_folder, normalized_old_name)
                new_path = os.path.join(self.cdn_folder, normalized_new_name)
                
                # Eski klasör var mı kontrol et
                if not os.path.exists(old_path) or not os.path.isdir(old_path):
                    return jsonify({"success": False, "message": "Collection directory not found"}), 404
                
                # Yeni isimde klasör var mı kontrol et
                if os.path.exists(new_path):
                    return jsonify({"success": False, "message": "A directory with this name already exists"}), 400
                
                # Klasörü yeniden adlandır
                os.rename(old_path, new_path)
                
                # Koleksiyon adını güncelle
                collection.name = new_name
                
                # Koleksiyondaki dosyaların yollarını güncelle
                for file in collection.files:
                    file.file_path = file.file_path.replace(old_name + '/', new_name + '/')
                
                session.commit()
                
                return jsonify({
                    "success": True, 
                    "message": "Collection updated successfully",
                    "collection": collection.to_dict()
                }), 200
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def get_admin_stats(self):
        """Admin paneli için istatistikler (sadece admin kullanıcılar)"""
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
            
            # Admin kontrolü
            self.auth_service.verify_admin(user_id)
            
            session = self.Session()
            try:
                from sqlalchemy import func
                
                # Toplam dosya sayısı ve boyutu
                file_stats = session.query(
                    func.count(File.id).label('total_files'),
                    func.sum(File.file_size).label('total_size')
                ).first()
                
                # Koleksiyon sayısı
                collection_count = session.query(func.count(Collection.id)).scalar()
                
                # Son eklenen dosyalar
                recent_files = session.query(File).order_by(File.created_at.desc()).limit(5).all()
                recent_files_list = []
                base_url = request.host_url.rstrip("/")
                
                for file in recent_files:
                    file_dict = file.to_dict()
                    file_dict["url"] = f"{base_url}/cdn/{file.file_path}"
                    recent_files_list.append(file_dict)
                
                # Koleksiyonlar
                collections = session.query(Collection).order_by(Collection.file_count.desc()).limit(5).all()
                collection_list = [collection.to_dict() for collection in collections]
                
                return jsonify({
                    "total_files": file_stats.total_files or 0,
                    "total_size": file_stats.total_size or 0,
                    "collection_count": collection_count,
                    "recent_files": recent_files_list,
                    "top_collections": collection_list
                })
            finally:
                session.close()
                
        except jwt.ExpiredSignatureError:
            abort(403, description="Forbidden: Token has expired")
        except jwt.InvalidTokenError:
            abort(403, description="Forbidden: Invalid token")
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500 