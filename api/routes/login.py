# --- Imports Padrão e OAuth ---
from fastapi import HTTPException, Depends, Request, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from urllib.parse import urlencode

# --- Imports da Aplicação ---
# CORREÇÃO 1: 'deps' -> 'src.database'
from src.database import get_db 
# CORREÇÃO 2: 'User' -> 'Usuario'
from src.models.usuario import Usuario 
from api.config import oauth, settings 
from src.security import autenticar_usuario, criar_token_de_acesso

# --- Novos Imports para Telefone e Twilio ---
import random
import os
from pydantic import BaseModel
from twilio.rest import Client

# Usar o primeiro da lista de settings como padrão
FRONTEND_URL = settings.FRONTEND_URLS[0] if settings.FRONTEND_URLS else "http://localhost:3000"

# Crie o router ANTES de usá-lo
router = APIRouter(tags=["Autênticação"])

# ... (Modelos Pydantic e temp_storage) ...
class RequestCodeBody(BaseModel):
    phone: str

class VerifyCodeBody(BaseModel):
    phone: str
    # CORREÇÃO 3: Faltava o campo 'code' que a rota usa
    code: str 
    
temp_code_storage = {}


# --- LOGIN COM GOOGLE ---

@router.get("/google")
async def login_google(request: Request):
    """
    Inicia o fluxo de login com o Google, redirecionando o usuário.
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    print("---------------------------------")
    print(f"PASSO 1 (LOGIN): Iniciando. Salvando sessão...")
    response = await oauth.google.authorize_redirect(request, redirect_uri)
    print(f"PASSO 1 (LOGIN): Sessão antes do redirect: {request.session}")
    print("---------------------------------")
    return response


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback do Google. Processa e redireciona para o frontend com o token.
    """
    print("---------------------------------")
    print(f"PASSO 2 (CALLBACK): Recebido. Lendo sessão...")
    print(f"PASSO 2 (CALLBACK): Sessão na chegada: {request.session}")
    print("---------------------------------")
    
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        print(f"!!! ERRO NO authorize_access_token: {e}")
        print(f"Sessão após o erro: {request.session}")
        raise e
        
    print("PASSO 3 (SUCESSO): Token autorizado!")
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Não foi possível obter informações do usuário do Google.")

    email = user_info["email"]
    # CORREÇÃO 4: 'User' -> 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.email == email).first()

    if not db_user:
        # CORREÇÃO 5: 'User' -> 'Usuario'
        db_user = Usuario(
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
    return await oauth.facebook.authorize_redirect(
        request, 
        settings.FACEBOOK_REDIRECT_URI,
        scope="email public_profile" 
    )


@router.get("/facebook/callback")
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.facebook.authorize_access_token(request)
    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
    profile = resp.json()
    email = profile.get("email")
    if not email:
        raise HTTPException(
            status_code=400, 
            detail="O provedor do Facebook não forneceu um e-mail."
        )
    # CORREÇÃO 6: 'User' -> 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.email == email).first()
    if not db_user:
        # CORREÇÃO 7: 'User' -> 'Usuario'
        db_user = Usuario(
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
    # 'autenticar_usuario' já foi corrigido para usar 'Usuario'
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
    # Retorna o token E os dados do usuário
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": usuario # Envia o objeto do usuário
    }


# --- LOGIN COM TELEFONE (ETAPA 1: Enviar Código) ---

@router.post("/phone/request-code")
async def request_phone_code(body: RequestCodeBody):
    if len(body.phone) < 10: 
        raise HTTPException(status_code=400, detail="Telefone inválido.")
    code = str(random.randint(100000, 999999))
    temp_code_storage[body.phone] = code
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
        if not all([account_sid, auth_token, twilio_phone]):
            print("!!! ERRO DE CONFIGURAÇÃO: Variáveis Twilio não definidas no .env")
            raise HTTPException(status_code=500, detail="Serviço de SMS não configurado.")
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Seu código de login iFome é: {code}",
            from_=twilio_phone,
            to=body.phone  
        )
        print(f"SMS enviado para {body.phone}. SID: {message.sid}")
    except Exception as e:
        print(f"!!! ERRO AO ENVIAR SMS: {e}")
        # Em desenvolvimento, retorne o código para facilitar o teste
        # Em produção, comente a linha abaixo e descomente a 'raise'
        return {"message": f"Erro (dev mode): Código seria {code}"}
        # raise HTTPException(status_code=500, detail="Erro ao enviar o código SMS.")
    
    return {"message": "Código enviado com sucesso!"}


# --- LOGIN COM TELEFONE (ETAPA 2: Verificar Código) ---

@router.post("/phone/verify-code")
async def verify_phone_code(body: VerifyCodeBody, db: Session = Depends(get_db)):
    stored_code = temp_code_storage.get(body.phone)
    if not stored_code:
        raise HTTPException(status_code=404, detail="Nenhum código solicitado para este número.")
    if stored_code != body.code:
        raise HTTPException(status_code=400, detail="Código inválido.")
    
    del temp_code_storage[body.phone]
    
    # CORREÇÃO 8: 'User' -> 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.telefone == body.phone).first()
    
    if not db_user:
        # CORREÇÃO 9: 'User' -> 'Usuario'
        db_user = Usuario(
            telefone=body.phone,
            nome_completo=f"Usuário {body.phone}",
            # Telefone não pode ser usado para email, então criamos um placeholder
            email=f"{body.phone}@phone.placeholder", 
            hashed_password="phone_oauth_placeholder",
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
    # O 'sub' do token deve ser algo único. Usaremos o email (mesmo que seja placeholder)
    access_token = criar_token_de_acesso(data={"sub": db_user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": db_user # Retorna o usuário
    }