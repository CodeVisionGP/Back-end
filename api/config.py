import os
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# Carrega variáveis do .env
load_dotenv()

# --- CLASSE DE CONFIGURAÇÃO (Sua Estrutura) ---

class Settings:
    # Configurações gerais
    PROJECT_NAME: str = "Backend Integrado"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # CORS
    FRONTEND_URLS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # Banco de dados
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "senha")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "ifome")

    DATABASE_URL: str = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # Segurança / Sessão
    SECRET_KEY: str = os.getenv("SECRET_KEY", "uma_chave_secreta_padrao")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia
    
    # --- CORREÇÃO 1: Carregar a base URL do .env ---
    NGROK_BASE_URL: str = os.getenv("NGROK_BASE_URL", "http://localhost:8000")

    # OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    FACEBOOK_CLIENT_ID: str = os.getenv("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    
    # --- CORREÇÃO 2: REMOVER AS DEFINIÇÕES DAQUI ---
    # As linhas GOOGLE_REDIRECT_URI e FACEBOOK_REDIRECT_URI foram movidas
    # para DEPOIS da criação da instância 'settings'.
    

settings = Settings()

# --- CORREÇÃO 3: Definir atributos dependentes NA INSTÂNCIA ---
# Isso garante que settings.NGROK_BASE_URL já exista e corrige o AttributeError.
settings.GOOGLE_REDIRECT_URI = f"{settings.NGROK_BASE_URL}/api/auth/google/callback"
settings.FACEBOOK_REDIRECT_URI = f"{settings.NGROK_BASE_URL}/api/auth/facebook/callback"


# --- CONFIGURAÇÃO DO AUTHLIB (OAuth) ---

config = Config(".env") 
oauth = OAuth(config)

# --- GOOGLE ---
# --- CORREÇÃO 4: Registrar a redirect_uri ---
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_REDIRECT_URI,  # <--- ESSA LINHA É A CORREÇÃO
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# --- FACEBOOK ---
# --- CORREÇÃO 4 (Bônus): Registrar a redirect_uri do Facebook também ---
oauth.register(
    name="facebook",
    client_id=settings.FACEBOOK_CLIENT_ID,
    client_secret=settings.FACEBOOK_CLIENT_SECRET,
    redirect_uri=settings.FACEBOOK_REDIRECT_URI, # <--- ESSA LINHA É A CORREÇÃO
    access_token_url="https://graph.facebook.com/oauth/access_token",
    authorize_url="https://www.facebook.com/dialog/oauth",
    api_base_url="https://graph.facebook.com/",
    client_kwargs={"scope": "email public_profile"},
)