import os
from dotenv import load_dotenv

# .env dosyasını yükle (varsa)
load_dotenv()

# Veritabanı ayarları
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "wallify")
DB_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# JWT ayarları
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", 365))

# Uygulama ayarları
PORT = int(os.getenv("PORT", 7545))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# CDN ayarları
CDN_FOLDER = os.getenv("CDN_FOLDER", os.path.join(os.getcwd(), "cdn")) 