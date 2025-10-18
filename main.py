import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from api.config import oauth, settings 
from api.routes import (
    consulta_restaurantes, 
    cadastro_endereco, 
    consulta_items, 
    cadastro_usuario, 
    cadastro_sacola, 
    login,
    payment_methods,
) 

from src.database import Base, engine 
from api.routes.cadastro_endereco import EnderecoModel 


# Carrega variáveis do .env
load_dotenv()




app = FastAPI(title="Backend Integrado")

# --- Configuração do CORS ---
# Puxa URLs permitidas do objeto settings
origins = settings.FRONTEND_URLS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY, 
)

# --- Inclusão das Rotas da sua aplicação ---

app.include_router(cadastro_endereco.router)
app.include_router(consulta_items.router)
app.include_router(cadastro_usuario.router)
app.include_router(cadastro_sacola.router)
app.include_router(payment_methods.router)
# Rota de Restaurantes (Proxy para Google Places)

app.include_router(
    consulta_restaurantes.router,
    prefix="/api/restaurantes", 
    tags=["Restaurantes"]
)

# Rotas de autenticação (OAuth)
app.include_router(
    login.router,
    prefix="/api/auth",
    tags=["Autenticação"]
)

@app.get("/")
async def root():
    return {"message": "Backend funcionando"}
