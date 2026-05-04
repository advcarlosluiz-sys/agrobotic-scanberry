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

    # Detecção robusta de ambiente de produção (Vercel)
    IS_VERCEL = (
        os.environ.get('VERCEL') == '1'
        or bool(os.environ.get('VERCEL_URL', ''))
        or os.environ.get('VERCEL_ENV') in ('production', 'preview')
    )

    if IS_VERCEL and not _db_url:
        SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/scanberry.db'
    elif _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///scanberry.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    # Upload — usa /tmp no Vercel (único diretório gravável)
    UPLOAD_FOLDER = '/tmp/uploads' if IS_VERCEL else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads'
    )

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # Segurança de Sessão:
    # SESSION_COOKIE_SECURE = True exige HTTPS — desabilitar em desenvolvimento local
    SESSION_COOKIE_SECURE = IS_VERCEL  # True apenas em produção (Vercel usa HTTPS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 dias

    @staticmethod
    def init_app(app):
        """Inicializa diretórios necessários com segurança."""
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        except Exception:
            # Em ambientes como Vercel, pastas fora de /tmp são read-only
            pass
