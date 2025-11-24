import os
import requests
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder 
from sqlalchemy.orm import Session
from typing import List 
from datetime import datetime

# --- IMPORTAÇÕES ---
from src.database import get_db
from api.connection_manager import manager
from src import schemas 

from src.models.pedidos import OrderModel, OrderStatus
from src.models.items import Item as ItemModel
from src.models.usuario import Usuario # Importar Usuário para pegar o e-mail

# --- CONFIGURAÇÃO DO SERVIÇO DE E-MAIL (Reutilizado) ---
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://localhost:3001/api/nf/enviar")

async def enviar_email_status(destinatario: str, order_id: int, novo_status: str):
    """
    Envia um e-mail de notificação de mudança de status.
    Reutiliza o endpoint /nf/enviar do Node.js, mas mudamos o assunto e corpo.
    """
    if not EMAIL_SERVICE_URL or not destinatario or 'placeholder' in destinatario:
        return

    # Mensagens personalizadas por status
    mensagens = {
        "CONFIRMADO": "Seu pedido foi confirmado pelo restaurante e logo começará a ser preparado!",
        "EM_PREPARO": "Seu pedido está sendo preparado com todo cuidado.",
        "SAIU_PARA_ENTREGA": "Oba! Seu pedido saiu para entrega. Fique atento à campainha!",
        "CONCLUIDO": "Pedido entregue. Bom apetite e obrigado pela preferência!",
        "CANCELADO": "Infelizmente seu pedido foi cancelado. Entre em contato com o restaurante para mais detalhes."
    }
    
    msg_corpo = mensagens.get(novo_status, f"O status do seu pedido mudou para: {novo_status}")

    payload = {
        "to": destinatario,
        "orderId": order_id,
        "subject": f"Atualização do Pedido #{order_id}: {novo_status}",
        "bodyText": f"Olá! \n\n{msg_corpo}\n\nAcompanhe em tempo real no app.",
        # Não mandamos PDF de nota fiscal aqui, então mandamos null ou string vazia se a API Node exigir
        "pdfBase64": "", 
        "pdfPath": "" 
        # Nota: Se sua API Node valida obrigatoriedade de PDF, você teria que ajustar lá 
        # ou mandar um PDF "dummy" aqui. Vou assumir que podemos adaptar ou mandar vazio.
    }

    try:
        # Se a API Node.js exigir PDF obrigatório, podemos precisar ajustar o 'schema' no Node.js
        # para tornar o PDF opcional em notificações simples.
        # Por enquanto, vamos tentar enviar assim.
        await asyncio.to_thread(requests.post, EMAIL_SERVICE_URL, json=payload, timeout=5)
        print(f"E-mail de status {novo_status} enviado para {destinatario}")
    except Exception as e:
        print(f"Erro ao enviar e-mail de status: {e}")

# ===================================================================
# ROTEADOR 1: ADMIN DE PEDIDOS
# ===================================================================

router_pedidos = APIRouter(
    prefix="/api/restaurante/pedidos",
    tags=["Admin Restaurante (Pedidos)"]
)

@router_pedidos.patch("/{order_id}/status", response_model=schemas.OrderResponse)
async def update_order_status(
    order_id: int, 
    update_data: schemas.OrderStatusUpdate, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para o restaurante atualizar o status de um pedido.
    """
    from sqlalchemy.orm import joinedload
    
    # Busca o pedido E o usuário dono do pedido (para pegar o e-mail)
    db_order = db.query(OrderModel).options(
        joinedload(OrderModel.itens),
        joinedload(OrderModel.usuario) # <--- Carrega o usuário junto
    ).filter(OrderModel.id == order_id).first()
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )
        
    # Atualiza o status no banco
    novo_status = update_data.status
    db_order.status = novo_status
    
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar status no DB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar o status do pedido."
        )
    
    # --- 1. ENVIO DO WEBSOCKET ---
    try:
        order_dict = jsonable_encoder(db_order)
        await manager.broadcast_to_order(order_id, order_dict)
    except Exception as e:
        print(f"ALERTA: Falha ao enviar notificação WebSocket: {e}")
        
    # --- 2. ENVIO DE E-MAIL (NOVO) ---
    if db_order.usuario and db_order.usuario.email:
        # Dispara em background para não travar a resposta
        asyncio.create_task(enviar_email_status(
            destinatario=db_order.usuario.email,
            order_id=order_id,
            novo_status=novo_status
        ))
    
    return db_order

@router_pedidos.get("/", response_model=List[schemas.OrderResponse])
async def get_all_orders_for_restaurant(db: Session = Depends(get_db)):
    """
    Endpoint para o restaurante ver todos os pedidos
    """
    from sqlalchemy.orm import joinedload
    
    orders = db.query(OrderModel).options(
        joinedload(OrderModel.itens)
    ).order_by(OrderModel.id.desc()).all()
    
    return orders

# ===================================================================
# ROTEADOR 2: ADMIN DE CARDÁPIO (CADASTRAR ITENS)
# ===================================================================

router_cardapio = APIRouter(
    prefix="/api/restaurante/cardapio",
    tags=["Admin Restaurante (Cardápio)"]
)

@router_cardapio.post("/{google_place_id}/items", response_model=schemas.ItemResponse)
def create_item_for_restaurant(
    google_place_id: str,
    item_data: schemas.ItemCreate, 
    db: Session = Depends(get_db)
):
    """
    Cadastra um novo item (produto) para um restaurante específico.
    """
    
    db_item = ItemModel(
        **item_data.model_dump(),
        restaurant_id=google_place_id 
    )
    
    try:
        db.add(db_item)
        db.commit()
        db.refresh(db_item) 
        return db_item
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível cadastrar o item: {e}"
        )