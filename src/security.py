import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.config import Config

# --- CORREÇÃO DE IMPORT ---
# Importa o modelo 'Usuario' (em português)
from src.models.usuario import Usuario

# --- Configurações de Segurança ---
config = Config(".env")

SECRET_KEY = config("SECRET_KEY", default="sua_chave_secreta_super_segura")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # O token expira em 30 minutos

# --- Funções de Hash de Senha (bcrypt) ---

def get_password_hash(password: str) -> str:
    """Gera o hash de uma senha em texto plano."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)


# --- Função de Autenticação (Usada pelo Login) ---

def autenticar_usuario(db: Session, email: str, senha: str) -> Usuario | bool:
    """
    Verifica se um usuário existe e se a senha está correta.
    """
    # 1. Encontra o usuário pelo email (usando 'Usuario')
    db_user = db.query(Usuario).filter(Usuario.email == email).first()

    # 2. Se o usuário não existe, retorna Falso
    if not db_user:
        return False
        
    # 3. Se o usuário foi encontrado, verifica a senha
    if not verify_password(senha, db_user.hashed_password):
        return False

    # 4. Se a senha estiver correta, retorna o objeto do usuário
    return db_user


# --- Função de Criação de Token (Usada pelo Login) ---

def criar_token_de_acesso(data: dict) -> str:
    """
    Gera um novo token de acesso JWT.
    """
    dados_para_codificar = data.copy()
    
    # Define o tempo de expiração do token
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    dados_para_codificar.update({"exp": expira_em})
    
    # Codifica o token com a chave secreta e o algoritmo
    token_jwt_codificado = jwt.encode(dados_para_codificar, SECRET_KEY, algorithm=ALGORITHM)
    
    return token_jwt_codificado