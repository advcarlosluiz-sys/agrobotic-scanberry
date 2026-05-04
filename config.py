"""
Agrobotic ScanBerry — Configurações do Aplicativo
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base do aplicativo."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'scanberry-dev-key-change-in-production')
    # Banco de Dados
    _db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        
    if os.environ.get('VERCEL') and not _db_url:
        SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/scanberry.db'
    else:
        SQLALCHEMY_DATABASE_URI = _db_url or 'sqlite:///scanberry.db'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Upload
    if os.environ.get('VERCEL'):
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    # Segurança de Sessão (Importante para Vercel/HTTPS)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 dias
    
    @staticmethod
    def init_app(app):
        """Inicializa diretórios necessários com segurança."""
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        except:
            # Em ambientes como Vercel, pastas fora de /tmp são read-only
            pass
