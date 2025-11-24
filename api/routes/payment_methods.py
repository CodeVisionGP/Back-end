# ARQUIVO FINAL: api/routes/metodos_pagamento.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from src.database import get_db, Base # Importa a Base
# Se necessário, adicione aqui o import para a classe Usuario se ela for usada
# Ex: from .usuario import Usuario 


# --- MODELO GENÉRICO DE PAGAMENTO (EXISTENTE) ---
class PaymentMethodModel(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False) 
    codigo = Column(String, unique=True, nullable=False) 
    requer_troco = Column(Boolean, default=False) 
    ativo = Column(Boolean, default=True) 

# --- NOVO MODELO: CARTÕES SALVOS PELO USUÁRIO ---
class UserCardModel(Base):
    """
    Armazena os cartões tokenizados de um usuário.
    NUNCA armazene o PAN ou CVV.
    """
    __tablename__ = "user_cards"

    id = Column(Integer, primary_key=True, index=True)
    # user_id é a Chave Estrangeira para a tabela 'usuarios'
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False) 
    
    # 🔴 Tokenização: Campo principal
    token_gateway = Column(String, unique=True, nullable=False, index=True) 
    
    bandeira = Column(String, nullable=False)               
    ultimos_quatro_digitos = Column(String(4), nullable=False) 
    data_validade = Column(String(5), nullable=False)       
    
    apelido = Column(String, nullable=True)                 
    criado_em = Column(DateTime, default=datetime.utcnow)

# --- SCHEMAS DE DADOS (PYDANTIC) ---

# Schema Existente (Método Genérico)
class PaymentMethodResponse(BaseModel):
    id: int
    nome: str
    codigo: str
    requer_troco: bool
    ativo: bool

    class Config:
        from_attributes = True
        
# 🌟 NOVO: Schema para criar um novo cartão (Entrada)
class CardCreate(BaseModel):
    token_gateway: str = Field(..., description="Token seguro fornecido pelo processador de pagamento.")
    ultimos_quatro_digitos: str = Field(..., min_length=4, max_length=4)
    data_validade: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{2}\/\d{2}$", description="Formato MM/AA")
    bandeira: str = Field(..., description="Ex: VISA, MASTERCARD")
    apelido: Optional[str] = None
    
# 🌟 NOVO: Schema de Resposta para Cartão
class CardResponse(BaseModel):
    id: int
    user_id: int
    apelido: Optional[str]
    bandeira: str
    ultimos_quatro_digitos: str
    data_validade: str
    
    class Config:
        from_attributes = True


# --- ROTEADOR ---
router = APIRouter(
    prefix="/api/payment_methods", 
    tags=["Pagamento"]
)

# -----------------------------------------------------
# ROTA GENÉRICA (EXISTENTE)
# -----------------------------------------------------
@router.get("/", response_model=List[PaymentMethodResponse])
def get_payment_methods(db: Session = Depends(get_db)):
    """Consulta todos os métodos de pagamento ativos (PIX, DINHEIRO, CARTAO)."""
    
    methods = db.query(PaymentMethodModel).filter(PaymentMethodModel.ativo == True).all()
    
    if not methods:
        # MOCK DATA: Insere os dados de mock e os retorna
        initial_methods = [
             PaymentMethodModel(nome="PIX", codigo="PIX", requer_troco=False),
             PaymentMethodModel(nome="Cartão de Crédito/Débito", codigo="CARTAO", requer_troco=False),
             PaymentMethodModel(nome="Dinheiro", codigo="DINHEIRO", requer_troco=True),
        ]
        db.add_all(initial_methods)
        db.commit()
        methods = db.query(PaymentMethodModel).filter(PaymentMethodModel.ativo == True).all()
        
    return methods


# -----------------------------------------------------
# 🌟 NOVAS ROTAS DE CARTÃO (Específicas do Usuário)
# -----------------------------------------------------

@router.post("/cards/{user_id}", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def register_card(
    user_id: int, 
    card_data: CardCreate,
    db: Session = Depends(get_db)
):
    """
    Registra um novo cartão tokenizado para o usuário.
    """
    
    # 1. Verifica duplicidade pelo Token
    existing_card = db.query(UserCardModel).filter(
        UserCardModel.user_id == user_id,
        UserCardModel.token_gateway == card_data.token_gateway
    ).first()
    
    if existing_card:
        raise HTTPException(status_code=400, detail="Este cartão já está cadastrado.")

    # 2. Cria o novo modelo
    new_card = UserCardModel(
        user_id=user_id,
        token_gateway=card_data.token_gateway,
        ultimos_quatro_digitos=card_data.ultimos_quatro_digitos,
        data_validade=card_data.data_validade,
        bandeira=card_data.bandeira,
        apelido=card_data.apelido
    )
    
    # 3. Salva no banco
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    
    return new_card


@router.get("/cards/{user_id}", response_model=List[CardResponse])
def get_user_cards(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Lista todos os cartões salvos por um usuário."""
    
    cards = db.query(UserCardModel).filter(UserCardModel.user_id == user_id).all()
    
    return cards