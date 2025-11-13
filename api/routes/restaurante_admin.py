from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List 
from datetime import datetime

# --- IMPORTAÇÕES CORRIGIDAS ---
from src.database import get_db
from api.connection_manager import manager
from src import schemas 

# 1. Importar os MODELOS do lugar certo (src/models)
from src.models.pedidos import OrderModel, OrderStatus
from src.models.items import Item as ItemModel

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
    db_order = db.query(OrderModel).options(
        joinedload(OrderModel.itens)
    ).filter(OrderModel.id == order_id).first()
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )
        
    db_order.status = update_data.status
    
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar o status do pedido."
        )
    
    response_data = schemas.OrderResponse.from_attributes(db_order).model_dump()
    await manager.broadcast_to_order(order_id, response_data)
    
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