import os
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from src.database import get_db, Base # Importa Base do arquivo do banco de dados

# --- Modelo de Resposta Pydantic ---
class SacolaItem(BaseModel):
    # Campos que o cliente envia para adicionar um item
    item_id: int
    restaurant_id: str # O Place ID do restaurante
    quantidade: int = 1
    observacao: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- Esquema Pydantic para Atualização (NOVO) ---
class SacolaItemUpdate(BaseModel):
    quantidade: int # A única coisa que pode ser atualizada nesta rota

class SacolaItemResponse(SacolaItem):
    # Campos retornados após a criação/consulta
    id: int
    user_id: str
    
# --- Modelo de Item da Sacola (SQLAlchemy) ---
class SacolaItemModel(Base):
    __tablename__ = "sacola_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    restaurant_id = Column(String, index=True, nullable=False)
    item_id = Column(Integer, nullable=False) # Referência ao ID do Item
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False) # Preço no momento da compra
    observacao = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/sacola", 
    tags=["Sacola"]
)

# --- FUNÇÃO HELPER: MOCK DE PREÇO ---
def get_mock_price(item_id: int) -> float:
    """Retorna um preço mock (simulado) baseado no ID para testes."""
    if item_id == 101: return 35.90
    if item_id == 102: return 18.50
    if item_id == 103: return 6.00
    return 10.00 # Preço padrão

# --- ROTA: ADICIONAR ITEM À SACOLA (POST) ---
@router.post("/{user_id}", response_model=SacolaItemResponse, status_code=status.HTTP_201_CREATED)
def add_item_to_sacola(
    user_id: str, 
    item: SacolaItem, 
    db: Session = Depends(get_db)
):
    """Adiciona um item à sacola do usuário. Salva no banco de dados."""
    
    # 1. Simular obtenção do preço unitário atual
    preco_unitario = get_mock_price(item.item_id)
    
    # 2. Criar o novo item da sacola
    novo_item_sacola = SacolaItemModel(
        user_id=user_id,
        restaurant_id=item.restaurant_id,
        item_id=item.item_id,
        quantidade=item.quantidade,
        preco_unitario=preco_unitario,
        observacao=item.observacao,
        criado_em=datetime.utcnow()
    )

    # 3. Persistir no DB
    try:
        db.add(novo_item_sacola)
        db.commit()
        db.refresh(novo_item_sacola)
        
        # 4. Retornar a resposta formatada
        return SacolaItemResponse(
            id=novo_item_sacola.id,
            user_id=novo_item_sacola.user_id,
            item_id=novo_item_sacola.item_id,
            restaurant_id=novo_item_sacola.restaurant_id,
            quantidade=novo_item_sacola.quantidade,
            observacao=novo_item_sacola.observacao
        )

    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar item na sacola: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao adicionar item à sacola.")

# --- ROTA: CONSULTAR SACOLA (GET) ---
@router.get("/{user_id}", response_model=List[SacolaItemResponse])
def get_sacola(user_id: str, db: Session = Depends(get_db)):
    """Consulta todos os itens na sacola de um usuário."""
    
    itens = db.query(SacolaItemModel).filter(SacolaItemModel.user_id == user_id).all()
    
    if not itens:
        # Retorna lista vazia em vez de 404 se a sacola estiver vazia
        return [] 
        
    return itens

# --- NOVA ROTA: ATUALIZAR QUANTIDADE DO ITEM NA SACOLA (PUT) ---
@router.put("/{user_id}/{sacola_item_id}", response_model=SacolaItemResponse)
def update_item_quantity(
    user_id: str, 
    sacola_item_id: int,
    update_data: SacolaItemUpdate, # Recebe apenas a nova quantidade
    db: Session = Depends(get_db)
):
    """Atualiza a quantidade de um item específico na sacola."""
    
    # 1. Encontrar o item
    db_item = db.query(SacolaItemModel).filter(
        SacolaItemModel.id == sacola_item_id,
        SacolaItemModel.user_id == user_id
    ).first()

    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado na sacola do usuário especificado."
        )

    # 2. Validar a nova quantidade
    if update_data.quantidade <= 0:
        # Se a quantidade for zero ou negativa, sugere-se a exclusão (DELETE)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A quantidade deve ser maior que zero. Use a rota DELETE para remover."
        )

    # 3. Atualizar e Persistir
    try:
        db_item.quantidade = update_data.quantidade
        
        db.commit()
        db.refresh(db_item)
        
        # Retornar o item atualizado
        return db_item
    
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar item na sacola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao atualizar item na sacola."
        )


# --- ROTA: DELETAR ITEM DA SACOLA (DELETE) ---
@router.delete("/{user_id}/{sacola_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item_from_sacola(
    user_id: str, 
    sacola_item_id: int,  # O ID da linha na tabela sacola_items
    db: Session = Depends(get_db)
):
    """Remove um item específico da sacola do usuário pelo ID do registro."""
    
    # 1. Encontrar o item na sacola, garantindo que pertence ao usuário
    db_item = db.query(SacolaItemModel).filter(
        SacolaItemModel.id == sacola_item_id,
        SacolaItemModel.user_id == user_id
    ).first()

    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado na sacola do usuário especificado."
        )

    # 2. Deletar e Persistir
    try:
        db.delete(db_item)
        db.commit()
        # Retornamos 204 No Content (padrão para DELETE bem-sucedido)
        return {"detail": "Item removido com sucesso."}
    
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar item da sacola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao remover item da sacola."
        )