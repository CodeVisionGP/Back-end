import os
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from src.database import get_db, Base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field # <--- IMPORTAÇÃO ADICIONADA

# -------------------------------------
# NOVO MODELO DE RESPOSTA (PYDANTIC)
# -------------------------------------
class ItemResponse(BaseModel):
    id: int
    restaurant_id: str
    nome: str
    preco: float
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ativo: bool
    criado_em: datetime 

    # Configuração necessária para FastAPI converter modelos SQLAlchemy para Pydantic
    class Config:
        from_attributes = True # Novo padrão do Pydantic V2 (equivalente a orm_mode=True)
# -------------------------------------


# --- Modelo de Item (SQLAlchemy) ---
class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    # NOTE: O restaurant_id é o place_id do Google, que é uma string
    restaurant_id = Column(String, index=True, nullable=False) 
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    descricao = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    imagem_url = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/restaurants", # Corrigido para corresponder à inclusão no main.py
    tags=["Consulta de Items"]
)

# --- ROTA ---
@router.get("/{restaurant_id}/items", response_model=List[ItemResponse]) # <--- USANDO O NOVO MODELO PYDANTIC
def get_items_for_restaurant(restaurant_id: str, db: Session = Depends(get_db)):
    """
    Busca itens de menu para um determinado restaurante (usando o Place ID como restaurant_id).
    
    NOTA: Se a tabela estiver vazia, retornamos itens MOCK para que o Front-end teste a visualização.
    No projeto final, você deve ter dados reais no DB.
    """
    
    # 1. Tenta buscar no banco de dados
    items = db.query(ItemModel).filter(ItemModel.restaurant_id == restaurant_id).all()
    
    # 2. Se não houver itens no DB, retorna MOCK para teste
    if not items:
        # Se for um ID de restaurante real do Google (ex: o Place ID do seu teste),
        # você pode retornar mocks específicos.
        if restaurant_id.startswith('ChIJ') or restaurant_id == '4':
            # NOTE: Os mocks são formatados para corresponder ao modelo ItemResponse.
            return [
                {
                    "id": 101,
                    "restaurant_id": restaurant_id,
                    "nome": "Hambúrguer Gourmet Clássico",
                    "preco": 35.90,
                    "descricao": "Carne Angus, queijo cheddar, alface, tomate e molho especial.",
                    "categoria": "Lanches",
                    "ativo": True,
                    # O FastAPI/Pydantic serializa datetime para string ISO
                    "criado_em": datetime.utcnow() 
                },
                {
                    "id": 102,
                    "restaurant_id": restaurant_id,
                    "nome": "Porção de Batata Frita",
                    "preco": 18.50,
                    "descricao": "Batatas rústicas com alecrim.",
                    "categoria": "Acompanhamentos",
                    "ativo": True,
                    "criado_em": datetime.utcnow()
                },
                {
                    "id": 103,
                    "restaurant_id": restaurant_id,
                    "nome": "Coca-Cola Zero (Lata)",
                    "preco": 6.00,
                    "descricao": "Lata de 350ml.",
                    "categoria": "Bebidas",
                    "ativo": True,
                    "criado_em": datetime.utcnow()
                },
            ]
        
        # Caso contrário, se o ID não for de teste, informa que não há itens.
        raise HTTPException(status_code=404, detail="Nenhum item encontrado para este restaurante.")
        
    # 3. Retorna os itens reais do banco de dados (se encontrados)
    return items
