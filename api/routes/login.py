# --- Imports Padrão e OAuth ---
from fastapi import HTTPException, Depends, Request, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from urllib.parse import urlencode

# --- Imports da Aplicação ---
from deps import get_db
from src.models.usuario import User
from src.oauth import oauth
from src.security import autenticar_usuario, criar_token_de_acesso

# --- Novos Imports para Telefone e Twilio ---
import random
import os  # Para ler variáveis de ambiente (.env)
from pydantic import BaseModel
from twilio.rest import Client # O cliente da API do Twilio


# Esta é a variável que você precisa atualizar toda vez que o ngrok reiniciar
NGROK_BASE_URL = "https://unnoisily-prominent-ermelinda.ngrok-free.dev"

# Esta é a URL do seu frontend (rodando em https)
FRONTEND_URL = "https://localhost:3000"

# Crie o router ANTES de usá-lo
router = APIRouter(tags=["Autenticação"])

# --- Modelos Pydantic para Login por Telefone ---
class RequestCodeBody(BaseModel):
    phone: str

class VerifyCodeBody(BaseModel):
    phone: str
    code: str

# --- Armazenamento temporário (NÃO USE EM PRODUÇÃO!) ---
# Em produção, use um banco de dados ou um cache (Redis)
temp_code_storage = {}


# --- LOGIN COM GOOGLE ---

@router.get("/google")
async def login_google(request: Request):
    """
    Inicia o fluxo de login com o Google, redirecionando o usuário.
    """
    redirect_uri = f"{NGROK_BASE_URL}/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback do Google. Processa e redireciona para o frontend com o token.
    """
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Não foi possível obter informações do usuário do Google.")

    email = user_info["email"]
    db_user = db.query(User).filter(User.email == email).first()

    if not db_user:
        db_user = User(
            nome_completo=user_info.get("name", "Usuário Google"),
            email=email,
            hashed_password="google_oauth_placeholder", 
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    access_token = criar_token_de_acesso(data={"sub": db_user.email})

    params = {"token": access_token}
    redirect_url = f"{FRONTEND_URL}/auth/callback?{urlencode(params)}"
    
    return RedirectResponse(url=redirect_url)


# --- LOGIN COM FACEBOOK ---

@router.get("/facebook")
async def login_facebook(request: Request):
    """
    Inicia o fluxo de login com o Facebook.
    """
    redirect_uri = f"{NGROK_BASE_URL}/api/auth/facebook/callback"

    return await oauth.facebook.authorize_redirect(
        request, 
        redirect_uri,
        scope="email public_profile" 
    )


@router.get("/facebook/callback")
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback do Facebook. Processa e redireciona para o frontend com o token.
    """
    token = await oauth.facebook.authorize_access_token(request)
    
    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
    profile = resp.json()

    email = profile.get("email")
    if not email:
        raise HTTPException(
            status_code=400, 
            detail="O provedor do Facebook não forneceu um e-mail."
        )

    db_user = db.query(User).filter(User.email == email).first()

    if not db_user:
        db_user = User(
            nome_completo=profile.get("name", "Usuário Facebook"),
            email=email,
            hashed_password="facebook_oauth_placeholder",
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    access_token = criar_token_de_acesso(data={"sub": db_user.email})

    params = {"token": access_token}
    redirect_url = f"{FRONTEND_URL}/auth/callback?{urlencode(params)}"
    
    return RedirectResponse(url=redirect_url)


# --- LOGIN COM EMAIL E SENHA ---

@router.post("/login")
async def login_para_token_de_acesso(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Autentica um usuário com email (username) e senha.
    Retorna um token de acesso Bearer.
    """
    usuario = autenticar_usuario(db, form_data.username, form_data.password)
    
    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = criar_token_de_acesso(
        data={"sub": usuario.email}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# --- LOGIN COM TELEFONE (ETAPA 1: Enviar Código) ---

@router.post("/phone/request-code")
async def request_phone_code(body: RequestCodeBody):
    if len(body.phone) < 10: # Validação muito simples
        raise HTTPException(status_code=400, detail="Telefone inválido.")

    # Gera um código aleatório de 6 dígitos
    code = str(random.randint(100000, 999999))
    
    # Armazena o código temporariamente associado ao telefone
    temp_code_storage[body.phone] = code

    # --- INÍCIO DA LÓGICA REAL DE ENVIO DE SMS (TWILIO) ---
    try:
        # Pega as credenciais do ambiente (do arquivo .env)
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")

        if not all([account_sid, auth_token, twilio_phone]):
            print("!!! ERRO DE CONFIGURAÇÃO: Variáveis Twilio não definidas no .env")
            raise HTTPException(status_code=500, detail="Serviço de SMS não configurado.")

        client = Client(account_sid, auth_token)

        # ⚠️ IMPORTANTE: O número 'to' deve estar no formato E.164
        # Exemplo: +5511999998888 (para Brasil)
        message = client.messages.create(
            body=f"Seu código de login iFome é: {code}",
            from_=twilio_phone,
            to=body.phone  
        )
        
        print(f"SMS enviado para {body.phone}. SID: {message.sid}")

    except Exception as e:
        print(f"!!! ERRO AO ENVIAR SMS: {e}")
        # Se falhar, não informe o erro exato ao usuário por segurança
        raise HTTPException(status_code=500, detail="Erro ao enviar o código SMS.")
    # --- FIM DA LÓGICA REAL DE ENVIO DE SMS ---

    return {"message": "Código enviado com sucesso!"}


# --- LOGIN COM TELEFONE (ETAPA 2: Verificar Código) ---

@router.post("/phone/verify-code")
async def verify_phone_code(body: VerifyCodeBody, db: Session = Depends(get_db)):
    
    stored_code = temp_code_storage.get(body.phone)

    if not stored_code:
        raise HTTPException(status_code=404, detail="Nenhum código solicitado para este número.")

    if stored_code != body.code:
        raise HTTPException(status_code=400, detail="Código inválido.")

    # O código está correto! Limpa o código usado.
    del temp_code_storage[body.phone]

    # (Assumindo que seu model 'User' tem um campo 'telefone' que é único)
    db_user = db.query(User).filter(User.telefone == body.phone).first()

    if not db_user:
        # Cria um novo usuário se ele não existir
        db_user = User(
            telefone=body.phone,
            nome_completo=f"Usuário {body.phone}", # Placeholder
            hashed_password="phone_oauth_placeholder", # Placeholder
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    # Cria um token de acesso real usando sua função de segurança
    # O 'sub' (subject) do token será o telefone do usuário
    access_token = criar_token_de_acesso(data={"sub": db_user.telefone})

    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }