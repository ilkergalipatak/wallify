from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    def __init__(self, id=None, username=None, email=None, is_admin=False):
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self.api_key = secrets.token_hex(32)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_api_key(self):
        self.api_key = secrets.token_hex(32)
        return self.api_key
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Collection(Base):
    __tablename__ = 'collections'
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    file_count = Column(Integer, default=0)
    total_file_size = Column(BigInteger, default=0)  # Bayt cinsinden
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # İlişkiler
    files = relationship("File", back_populates="collection", cascade="all, delete-orphan")
    
    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "file_count": self.file_count,
            "total_file_size": self.total_file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_stats(self, session):
        """Koleksiyon istatistiklerini güncelle"""
        from sqlalchemy import func
        file_stats = session.query(
            func.count(File.id).label('file_count'),
            func.sum(File.file_size).label('total_size')
        ).filter(File.collection_id == self.id).first()
        
        self.file_count = file_stats.file_count or 0
        self.total_file_size = file_stats.total_size or 0
        self.updated_at = datetime.datetime.utcnow()

class File(Base):
    __tablename__ = 'files'
    
    id = Column(String, primary_key=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)  # Bayt cinsinden
    mime_type = Column(String)
    collection_id = Column(String, ForeignKey('collections.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # İlişkiler
    collection = relationship("Collection", back_populates="files")
    
    def __init__(self, file_name, file_path, file_size, mime_type=None, collection_id=None):
        self.id = str(uuid.uuid4())
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type
        self.collection_id = collection_id
        
    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "collection_id": self.collection_id,
            "collection_name": self.collection.name if self.collection else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 