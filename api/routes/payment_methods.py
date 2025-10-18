# api/routes/metodos_pagamento.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean
from pydantic import BaseModel
from typing import List

from src.database import get_db, Base # Importa Base do arquivo do banco de dados

# --- Modelo de Dados (SQLAlchemy) ---
class PaymentMethodModel(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)        # Ex: "Cartão de Crédito", "Dinheiro", "PIX"
    codigo = Column(String, unique=True, nullable=False)      # Ex: "CARTAO", "DINHEIRO", "PIX"
    requer_troco = Column(Boolean, default=False)             # Necessário para 'Dinheiro'
    ativo = Column(Boolean, default=True)                     # Se o método está ativo
    # Nota: Poderíamos adicionar campos para bandeiras de cartão (Visa/Master), etc.

# --- Modelo de Resposta Pydantic ---
class PaymentMethodResponse(BaseModel):
    id: int
    nome: str
    codigo: str
    requer_troco: bool
    ativo: bool

    class Config:
        from_attributes = True

# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/payment_methods", 
    tags=["Pagamento"]
)

# --- ROTA: CONSULTAR MÉTODOS DE PAGAMENTO ---
@router.get("/", response_model=List[PaymentMethodResponse])
def get_payment_methods(db: Session = Depends(get_db)):
    """Consulta todos os métodos de pagamento ativos."""
    
    # Busca apenas os métodos que estão ativos
    methods = db.query(PaymentMethodModel).filter(PaymentMethodModel.ativo == True).all()
    
    # Se o banco de dados estiver vazio, fornece um mock inicial para desenvolvimento
    if not methods:
        # MOCK DATA: Insere os dados de mock e os retorna
        initial_methods = [
            PaymentMethodModel(nome="PIX", codigo="PIX", requer_troco=False),
            PaymentMethodModel(nome="Cartão de Crédito/Débito", codigo="CARTAO", requer_troco=False),
            PaymentMethodModel(nome="Dinheiro", codigo="DINHEIRO", requer_troco=True),
        ]
        
        db.add_all(initial_methods)
        db.commit()
        
        # Busca novamente para incluir os IDs gerados
        methods = db.query(PaymentMethodModel).filter(PaymentMethodModel.ativo == True).all()
        
    return methods