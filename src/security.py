import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.config import Config

# Importa o modelo de usuário para que possamos consultá-lo
from src.models.usuario import User

# --- Configurações de Segurança ---

# Carrega as variáveis do .env (PRECISAMOS DA SECRET_KEY)
# Certifique-se de que seu arquivo .env tem a linha:
# SECRET_KEY=sua_chave_secreta_super_segura
config = Config(".env")

SECRET_KEY = config("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # O token expira em 30 minutos

# --- Funções de Hash de Senha (As que você já tinha) ---

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


# --- Função de Autenticação (A que faltava) ---

def autenticar_usuario(db: Session, email: str, senha: str) -> User | bool:
    """
    Verifica se um usuário existe e se a senha está correta.
    (Esta é a função que o 'login.py' tentava importar)
    """
    # 1. Encontra o usuário pelo email
    db_user = db.query(User).filter(User.email == email).first()

    # 2. Se o usuário não existe, retorna Falso
    if not db_user:
        return False
        
    # 3. Se o usuário foi encontrado, verifica a senha
    #    (Usando a sua função 'verify_password')
    if not verify_password(senha, db_user.hashed_password):
        return False

    # 4. Se a senha estiver correta, retorna o objeto do usuário
    return db_user


# --- Função de Criação de Token (A outra que faltava) ---

def criar_token_de_acesso(data: dict) -> str:
    """
    Gera um novo token de acesso JWT.
    (Esta é a outra função que o 'login.py' tentava importar)
    """
    dados_para_codificar = data.copy()
    
    # Define o tempo de expiração do token
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    dados_para_codificar.update({"exp": expira_em})
    
    # Codifica o token com a chave secreta e o algoritmo
    token_jwt_codificado = jwt.encode(dados_para_codificar, SECRET_KEY, algorithm=ALGORITHM)
    
    return token_jwt_codificado

# (Você também pode adicionar uma função 'verificar_token_acesso' aqui
#  para proteger rotas no futuro, mas por enquanto isso é o suficiente
#  para fazer o login funcionar.)