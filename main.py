import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from api.config import settings 
from src.database import Base, engine 
from src.models import (
    usuario, 
    endereco, 
    items, 
    pedidos,
    avaliacao
)
from api.routes import cadastro_sacola as sacola_model 
from api.routes import relatorios
# --- 2. IMPORTAR ROTEADORES ---
from api.routes import (
    consulta_restaurantes, 
    cadastro_endereco, 
    consulta_items, 
    cadastro_usuario, 
    login,
    payment_methods,
    pedidos, 
    restaurante_admin,
    avaliacao 
) 

# Importa o manager
from api.connection_manager import manager

load_dotenv()

# Cria as tabelas se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Backend Integrado")

# --- Middlewares ---
origins = ["*"] 

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
    https_only=False,
    same_site='lax'
)

# --- 4. ROTAS ---
app.include_router(cadastro_endereco.router)
app.include_router(cadastro_usuario.router) 
app.include_router(sacola_model.router) 
app.include_router(payment_methods.router)
app.include_router(pedidos.router)
app.include_router(relatorios.router)
app.include_router(avaliacao.router)
app.include_router(restaurante_admin.router_pedidos)
app.include_router(restaurante_admin.router_cardapio)

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
app.include_router(
    login.router,
    prefix="/api/auth",
    tags=["Autênticação"]
)

# --- 5. ENDPOINT DE WEBSOCKET ---
@app.websocket("/ws/order/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: int):
    await manager.connect(websocket, order_id)
    try:
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, order_id)
        
    except Exception as e:
        print(f"Erro no WebSocket [Order ID: {order_id}]: {e}")
        manager.disconnect(websocket, order_id)

@app.get("/")
async def root():
    return {"message": "Backend funcionando"}