import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect # AQUI <<<
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from api.config import oauth, settings 
from fastapi import HTTPException
from typing import List, Optional
import json # AQUI <<<

# --- 1. IMPORTAR OS ROUTERS ---
from api.routes import (
    consulta_restaurantes, 
    cadastro_endereco, 
    consulta_items, 
    cadastro_usuario, 
    cadastro_sacola, 
    login,
    payment_methods,
    pedidos,
    restaurante_admin,
    usuarios
) 

# --- AQUI <<< 1.b IMPORTAR O GERENCIADOR DE CONEXÃO ---
from api.connection_manager import manager


# --- 2. IMPORTAR O BANCO E OS MODELOS ---
from src.database import Base, engine 
from src.models import usuario, endereco, items, sacola_model 

# Carrega variáveis do .env
load_dotenv()

# --- 3. CRIAR AS TABELAS NO BANCO ---
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Backend Integrado")

# --- Configuração do CORS ---
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

# --- 4. INCLUSÃO DAS ROTAS ---

app.include_router(cadastro_endereco.router)
app.include_router(cadastro_usuario.router)
app.include_router(usuarios.router)
app.include_router(cadastro_sacola.router)
app.include_router(payment_methods.router)
app.include_router(pedidos.router)
app.include_router(restaurante_admin.router)
app.include_router(
    consulta_items.router,
    prefix="/api/restaurants", 
    tags=["Itens do Restaurante"] 
)

app.include_router(
    consulta_restaurantes.router,
    prefix="/api/restaurantes", 
    tags=["Restaurantes"]
)

# Rotas de autenticação (OAuth)
app.include_router(
    login.router,
    prefix="/api/auth",
    tags=["Autênticação"]
)

# --- AQUI <<< 5. ENDPOINT DE WEBSOCKET ---
@app.websocket("/ws/order/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: int):
    """
    Endpoint WebSocket para clientes ouvirem atualizações
    de um pedido específico.
    """
    
    # 1. Conecta o cliente ao gerenciador
    await manager.connect(websocket, order_id)
    
    try:
        # 2. Mantém a conexão viva
        while True:
            # Apenas espera por mensagens (ex: pings)
            # ou até o cliente desconectar.
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        # 3. Limpa a conexão se o cliente desconectar
        manager.disconnect(websocket, order_id)
        
    except Exception as e:
        # 4. Lida com outros erros
        print(f"Erro no WebSocket [Order ID: {order_id}]: {e}")
        manager.disconnect(websocket, order_id)


@app.get("/")
async def root():
    return {"message": "Backend funcionando"}
