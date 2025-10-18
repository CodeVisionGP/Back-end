from fastapi import HTTPException, Depends, Request, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from deps import get_db
from src.models.usuario import User
from src.oauth import oauth
from src.security import autenticar_usuario, criar_token_de_acesso

router = APIRouter(tags=["Autenticação"])

# URL do seu frontend
FRONTEND_URL = "http://localhost:3000"

# --- LOGIN COM GOOGLE ---

@router.get("/google")
async def login_google(request: Request):
    """
    Inicia o fluxo de login com o Google, redirecionando o usuário.
    """
    # O nome da rota de callback deve corresponder ao nome da função abaixo
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback do Google. Recebe o usuário, cria ou busca no banco,
    gera um token JWT e redireciona para o frontend com o token.
    """
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Não foi possível obter informações do usuário do Google.")

    email = user_info["email"]
    db_user = db.query(User).filter(User.email == email).first()

    if not db_user:
        # Cria um novo usuário se ele não existir
        db_user = User(
            nome_completo=user_info.get("name", "Usuário Google"),
            email=email,
            hashed_password="google_oauth_placeholder", # Senha não é usada para logins sociais
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # ALTERADO: Em vez de redirecionar direto, criamos um token
    access_token = criar_token_de_acesso(data={"sub": db_user.email})

    # ALTERADO: Redirecionamos para uma página de callback no frontend, passando o token
    params = {"token": access_token}
    redirect_url = f"{FRONTEND_URL}/auth/callback?{urlencode(params)}"
    
    return RedirectResponse(url=redirect_url)


# --- LOGIN COM FACEBOOK ---

@router.get("/facebook")
async def login_facebook(request: Request):
    """
    Inicia o fluxo de login com o Facebook.
    """
    # O Facebook exige que os campos (scope) sejam definidos. 'email' é fundamental.
    redirect_uri = request.url_for("facebook_callback")
    return await oauth.facebook.authorize_redirect(
        request, 
        str(redirect_uri),
        scope="email public_profile" # Solicitando explicitamente e-mail e nome
    )


@router.get("/facebook/callback")
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    """
    Callback do Facebook. Processa o login e redireciona para o frontend com o token.
    """
    token = await oauth.facebook.authorize_access_token(request)
    
    # Faz uma chamada para obter os campos básicos do perfil
    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
    profile = resp.json()

    email = profile.get("email")
    if not email:
        # Erro comum se o usuário não permitir o e-mail ou se o e-mail for privado/não verificado no Facebook
        raise HTTPException(
            status_code=400, 
            detail="O provedor do Facebook não forneceu um e-mail. Verifique suas permissões no Facebook."
        )

    # Lógica de criação/busca de usuário no banco (igual ao Google)
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

    # Criação do token JWT e redirecionamento
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
