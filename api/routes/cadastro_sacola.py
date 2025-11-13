import os
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from src.database import get_db, Base 

# --- 1. Modelo de Entrada Pydantic ---
class SacolaItem(BaseModel):
    item_id: int
    restaurant_id: str 
    quantidade: int = 1
    observacao: Optional[str] = None
    nome: str
    preco: float

# --- 2. Modelo de Resposta Pydantic ---
class SacolaItemResponse(BaseModel):
    id: int
    user_id: str
    item_id: int
    restaurant_id: str
    quantidade: int
    observacao: Optional[str] = None
    nome: str
    preco_unitario: float

    class Config:
        from_attributes = True

# --- Esquema Pydantic para Atualização ---
class SacolaItemUpdate(BaseModel):
    quantidade: int

# --- 3. Modelo de Item da Sacola (SQLAlchemy / Tabela) ---
class SacolaItemModel(Base):
    __tablename__ = "sacola_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) 
    restaurant_id = Column(String, index=True, nullable=False)
    item_id = Column(Integer, nullable=False)
    nome = Column(String, nullable=False, default="Item") 
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False)
    observacao = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/sacola", 
    tags=["Sacola"]
)

# --- ROTA: ADICIONAR ITEM À SACOLA (POST) ---
@router.post("/{user_id}", response_model=SacolaItemResponse, status_code=status.HTTP_200_OK)
def add_item_to_sacola(
    user_id: str, 
    item: SacolaItem,
    db: Session = Depends(get_db)
):
    """
    Adiciona um item à sacola. 
    Se o item já existir, atualiza a quantidade.
    """
    
    # --- LÓGICA DE CORREÇÃO ---
    # 1. Procura se o item JÁ ESTÁ na sacola do usuário
    item_existente = db.query(SacolaItemModel).filter(
        SacolaItemModel.user_id == user_id,
        SacolaItemModel.item_id == item.item_id,
        SacolaItemModel.restaurant_id == item.restaurant_id
    ).first()
    
    try:
        if item_existente:
            # 2. Se JÁ EXISTE, apenas soma a quantidade
            item_existente.quantidade += item.quantidade
            db.commit()
            db.refresh(item_existente)
            return item_existente
        
        else:
            # 3. Se NÃO EXISTE, cria um novo
            novo_item_sacola = SacolaItemModel(
                user_id=user_id,
                restaurant_id=item.restaurant_id,
                item_id=item.item_id,
                nome=item.nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco,
                observacao=item.observacao,
                criado_em=datetime.utcnow()
            )
            db.add(novo_item_sacola)
            db.commit()
            db.refresh(novo_item_sacola)
            return novo_item_sacola

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
        return [] 
    return itens

# --- ROTA: ATUALIZAR QUANTIDADE (PUT) ---
@router.put("/{user_id}/{sacola_item_id}", response_model=SacolaItemResponse)
def update_item_quantity(
    user_id: str, 
    sacola_item_id: int,
    update_data: SacolaItemUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza a quantidade de um item específico na sacola."""
    
    db_item = db.query(SacolaItemModel).filter(
        SacolaItemModel.id == sacola_item_id,
        SacolaItemModel.user_id == user_id
    ).first()

    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado na sacola."
        )

    if update_data.quantidade <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A quantidade deve ser maior que zero. Use DELETE para remover."
        )

    try:
        db_item.quantidade = update_data.quantidade
        db.commit()
        db.refresh(db_item)
        return db_item
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao atualizar item."
        )

# --- ROTA: DELETAR ITEM DA SACOLA (DELETE) ---
@router.delete("/{user_id}/{sacola_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item_from_sacola(
    user_id: str, 
    sacola_item_id: int,
    db: Session = Depends(get_db)
):
    """Remove um item específico da sacola do usuário pelo ID do registro."""
    
    db_item = db.query(SacolaItemModel).filter(
        SacolaItemModel.id == sacola_item_id,
        SacolaItemModel.user_id == user_id
    ).first()

    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado na sacola."
        )

    try:
        db.delete(db_item)
        db.commit()
        return {"detail": "Item removido com sucesso."}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao remover item."
        )