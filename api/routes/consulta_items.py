import os
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

# --- Nossas Importações Locais Corrigidas ---
from src.database import get_db
from src.models.items import Item  # <-- CORRETO
from src import schemas          # <-- CORRETO

# --- ROTEADOR ---
router = APIRouter(
    # Eu sugiro adicionar um prefixo aqui para organizar
    # Ex: prefix="/cardapio"
    tags=["Consulta de Itens"]
)

# --- ROTA ---
# Alterei a rota para /items/{restaurant_id} para ficar mais claro
@router.get("/items/{restaurant_id}", response_model=List[schemas.ItemResponse])
def get_items_for_restaurant(restaurant_id: str, db: Session = Depends(get_db)):
    """
    Busca itens de menu para um determinado restaurante (usando o Place ID).
    """
    
    # --- LÓGICA DE MOCK (SOMENTE PARA TESTES) ---
    # Se o ID for 'mock-id', retorna dados falsos para o frontend testar.
    if restaurant_id == "mock-id":
        return [
            {
                "id": 101,
                "restaurant_id": restaurant_id,
                "nome": "Hambúrguer Gourmet",
                "preco": 35.90,
                "descricao": "Carne Angus, queijo cheddar, alface, tomate e molho especial.",
                "categoria": "Lanches",
                "ativo": True,
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
        ]

    # --- LÓGICA REAL (BUSCA NO BANCO DE DADOS) ---
    
    # 1. Tenta buscar no banco de dados usando o MODELO importado
    #    Boa prática: Adicionado filtro para 'Item.ativo == True'
    items = db.query(Item).filter(
        Item.restaurant_id == restaurant_id,
        Item.ativo == True
    ).all()
    
    # 2. Retorna os itens encontrados (ou uma lista vazia)
    #    O Pydantic (via response_model) garante a conversão
    #    Se 'items' for uma lista vazia, ele retornará '[]',
    #    o que é perfeito para o frontend.
    return items