from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List # AQUI <<< Importação para corrigir o erro "List is not defined"

from src.database import get_db

# --- IMPORTANTE ---
# Reutilizar os modelos e Enums
from api.routes.pedidos import OrderModel, OrderStatus, OrderResponse

# --- AQUI <<< Importar o gerenciador de WebSocket ---
from api.connection_manager import manager

# ===================================================================
# 1. MODELO PYDANTIC (Requisição)
# ===================================================================

class OrderStatusUpdate(BaseModel):
    """
    Modelo que o restaurante enviará no corpo (body) da requisição
    para atualizar um status.
    """
    status: OrderStatus # Ex: { "status": "EM_PREPARO" }

# ===================================================================
# 2. ROTEADOR (Admin do Restaurante)
# ===================================================================

router = APIRouter(
    prefix="/api/restaurante/pedidos",
    tags=["Admin Restaurante"]
)

# ===================================================================
# 3. ENDPOINT DE ATUALIZAÇÃO (PATCH)
# ===================================================================

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status( # AQUI <<< Função agora é 'async def'
    order_id: int, 
    update_data: OrderStatusUpdate, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para o restaurante atualizar o status de um pedido.
    (Ex: de 'PENDENTE' para 'CONFIRMADO')
    """
    
    # 1. Encontra o pedido no banco
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )
        
    # 2. Atualiza o status
    print(f"Atualizando pedido {order_id} de '{db_order.status.value}' para '{update_data.status.value}'")
    db_order.status = update_data.status
    
    # 3. Salva a mudança
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar o status do pedido."
        )
    
    # --- AQUI <<< 4. DISPARAR NOTIFICAÇÃO WEBSOCKET ---
    # Serializa o pedido atualizado usando o Pydantic
    response_data = OrderResponse.from_attributes(db_order).model_dump()
    
    # Envia os dados para todos os clientes ouvindo este order_id
    await manager.broadcast_to_order(order_id, response_data)
    # --- FIM DA ADIÇÃO ---
    
    # 5. Retorna o pedido completo e atualizado
    return db_order

@router.get("/", response_model=List[OrderResponse])
async def get_all_orders_for_restaurant(db: Session = Depends(get_db)): # AQUI <<< Função agora é 'async def'
    """
    Endpoint para o restaurante ver todos os pedidos
    (ex: um painel de controle).
    """
    orders = db.query(OrderModel).order_by(OrderModel.id.desc()).all()
    return orders
