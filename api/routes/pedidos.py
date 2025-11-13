from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# --- IMPORTAÇÕES CORRIGIDAS ---
from src.database import get_db
# 1. Importar os MODELOS do lugar certo (src/models)
#    (NÃO defina 'class OrderModel' aqui)
from src.models.pedidos import OrderModel, PedidoItem, OrderStatus
from src.models.items import Item as ItemModel
# 2. Importar os SCHEMAS
from src import schemas

# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/pedidos",
    tags=["Pedidos (Cliente)"]
)

# --- ROTAS ---
@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    pedido_data: schemas.PedidoCreate,
    db: Session = Depends(get_db)
    # TODO: user_id = Depends(get_current_user)
):
    """
    Cria um novo pedido (chamado pelo cliente ao fechar o carrinho).
    """
    
    itens_para_salvar_no_db = []
    preco_total_calculado = 0.0

    # 1. VALIDAÇÃO: Pega os itens do carrinho e busca no banco
    for item_carrinho in pedido_data.itens_do_carrinho:
        
        item_db = db.query(ItemModel).filter(
            ItemModel.id == item_carrinho.item_id,
            ItemModel.ativo == True
        ).first()
        
        if not item_db:
            raise HTTPException(
                status_code=404, 
                detail=f"Item ID {item_carrinho.item_id} não encontrado ou inativo."
            )
        
        # 2. CÁLCULO: Calcula o subtotal e o total
        preco_unitario_real = item_db.preco
        preco_total_calculado += (preco_unitario_real * item_carrinho.quantidade)
        
        # 3. PREPARAÇÃO: Cria o objeto PedidoItem (sem salvar ainda)
        novo_item_pedido = PedidoItem(
            item_id=item_db.id,
            quantidade=item_carrinho.quantidade,
            preco_unitario_pago=preco_unitario_real
        )
        itens_para_salvar_no_db.append(novo_item_pedido)

    if not itens_para_salvar_no_db:
        raise HTTPException(status_code=400, detail="Carrinho vazio.")

    # 4. CRIAÇÃO DO PEDIDO "PAI"
    novo_pedido = OrderModel(
        # TODO: user_id=user.id (ID do usuário logado)
        user_id=1, # <--- MUDANÇA TEMPORÁRIA (use 1 como placeholder)
        status=OrderStatus.PENDENTE, # O status inicial
        total_price=preco_total_calculado,
        restaurante_id=pedido_data.restaurante_id
    )

    # 5. ASSOCIAÇÃO: "Pendura" os itens no pedido
    novo_pedido.itens = itens_para_salvar_no_db
    
    # 6. SALVAR TUDO (Transação)
    try:
        db.add(novo_pedido) 
        db.commit()
        db.refresh(novo_pedido)
        
        # (Aqui você também pode disparar um WebSocket para o restaurante!)
        
        return novo_pedido
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao salvar pedido no banco: {e}"
        )