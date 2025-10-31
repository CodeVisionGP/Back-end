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
# CORRETO: O router não tem prefixo, 
# ele será definido no main.py
router = APIRouter(
    tags=["Consulta de Items"]
)

# --- ROTA ---
@router.get("/{restaurant_id}/items", response_model=List[schemas.ItemResponse])
def get_items_for_restaurant(restaurant_id: str, db: Session = Depends(get_db)):
    """
    Busca itens de menu para um determinado restaurante (usando o Place ID como restaurant_id).
    
    NOTA: Se a tabela estiver vazia, retornamos itens MOCK para que o Front-end teste a visualização.
    """
    
    # 1. Tenta buscar no banco de dados usando o MODELO importado
    items = db.query(Item).filter(Item.restaurant_id == restaurant_id).all() # <-- CORRETO
    
    # 2. Se houver itens reais no banco, retorna eles
    if items:
        # O Pydantic (via response_model) garante a conversão
        return items

    # 3. Se não houver itens no DB, verifica se é um ID de MOCK para teste
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
        
    # 4. CORREÇÃO: Se não for um mock e o banco estiver vazio,
    # retorna uma LISTA VAZIA, e não um 404.
    # Isso permite o frontend mostrar a tela de "Nenhum item disponível".
    return []