import re
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum 

# -------------------------------------------------------------------
# --- ENUMS ---
# -------------------------------------------------------------------

class OrderStatus(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    EM_PREPARO = "EM_PREPARO"
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"

class TipoEntrega(str, Enum):
    NORMAL = "NORMAL"
    RAPIDA = "RAPIDA"
    AGENDADA = "AGENDADA"

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# -------------------------------------------------------------------
# --- SCHEMAS DE ENTIDADES (BASE) ---
# -------------------------------------------------------------------

class UserBase(BaseSchema):
    nome_completo: str
    email: Optional[EmailStr] = None
    telefone: str
    is_active: bool = True
class UserCreate(UserBase):
    senha: str = Field(..., min_length=6)
class UserResponse(UserBase):
    id: int
class EnderecoBase(BaseSchema):
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str
    complemento: Optional[str] = None
    referencia: Optional[str] = None
    
    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v): return v.upper()
    
    @field_validator("cep")
    @classmethod
    def validar_cep(cls, v): return f"{v.replace('-', '')[:5]}-{v.replace('-', '')[5:]}" if re.match(r"^\d{5}-?\d{3}$", v) else v
class EnderecoCreate(EnderecoBase): pass
class EnderecoResponse(EnderecoBase):
    id: int
    user_id: int 
    latitude: Optional[float] = None
    longitude: Optional[float] = None
class ItemBase(BaseSchema):
    nome: str
    preco: float
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    imagem_url: Optional[str] = None
    ativo: bool = True
class ItemCreate(ItemBase): pass
class ItemResponse(ItemBase):
    id: int
    restaurant_id: str
    criado_em: datetime
class CartItem(BaseModel):
    item_id: int
    quantidade: int
class OrderStatusUpdate(BaseModel):
    status: OrderStatus 
class SacolaItemBase(BaseSchema):
    item_id: int
    quantidade: int
    restaurant_id: str
    nome: str
    preco: float
    observacao: Optional[str] = None
class SacolaItemCreate(SacolaItemBase): pass
class SacolaItemResponse(SacolaItemBase):
    id: int 
    user_id: str 
class SacolaResponse(BaseSchema):
    id: int
    user_id: int
    total_price: float
    status: str
    items: List[SacolaItemResponse]

# -------------------------------------------------------------------
# --- SCHEMAS DE PEDIDO (CHECKOUT - CORRIGIDO) ---
# -------------------------------------------------------------------

class PedidoItemResponse(BaseSchema):
    id: int
    item_id: int
    quantidade: int
    preco_unitario_pago: float

class PedidoCreate(BaseModel):
    """O que o front-end envia para criar um pedido"""
    restaurante_id: str 
    endereco_id: int
    itens_do_carrinho: List[CartItem]
    
    # 💳 CAMPOS DE PAGAMENTO (CORRIGIDOS)
    codigo_pagamento: str = Field(..., description="Código do método (PIX, CARTAO, DINHEIRO).")
    card_token: Optional[str] = Field(None, description="Token seguro do cartão salvo, se aplicável.")
    
    # 📝 CAMPO DE OBSERVAÇÕES
    observacoes: Optional[str] = Field(None, description="Observações gerais sobre o pedido.")
    
    # Campos de entrega
    tipo_entrega: TipoEntrega = TipoEntrega.NORMAL
    horario_entrega: Optional[str] = None


class ValidacaoEntrega(BaseModel):
    codigo: str


class OrderResponse(BaseSchema):
    """Resposta completa de um Pedido"""
    id: int
    user_id: int 
    restaurant_id: str 
    status: OrderStatus
    total_price: float
    criado_em: datetime
    

    tipo_entrega: TipoEntrega
    horario_entrega: Optional[str]
    
    codigo_entrega: Optional[str]

    itens: List[PedidoItemResponse] = []

# -------------------------------------------------------------------
# --- SCHEMAS DE AVALIAÇÃO ---
# -------------------------------------------------------------------

class AvaliacaoCreate(BaseModel):
    pedido_id: int
    nota: int
    comentario: Optional[str] = None

class AvaliacaoResponse(BaseSchema):
    id: int
    pedido_id: int
    nota: int
    comentario: Optional[str]
    criado_em: datetime
    
    class Config:
        from_attributes = True


# -------------------------------------------------------------------
# --- SCHEMAS DE TELA DE HISTORICO ---
# -------------------------------------------------------------------
        
class OrderHistoryResponse(BaseSchema):
    
    id: int
    restaurante_nome: str  
    status: OrderStatus
    total_price: float
    criado_em: datetime

    class Config:
        from_attributes = True