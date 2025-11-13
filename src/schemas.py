import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

# --- Importação de Enums (do seu arquivo de pedidos) ---
from enum import Enum 

class OrderStatus(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    EM_PREPARO = "EM_PREPARO"
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"

# --- Config base ---
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True # Novo padrão do Pydantic V2

# ====================================================================
# SCHEMAS DE ENDEREÇO
# ====================================================================

class EnderecoBase(BaseSchema):
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str = Field(..., description="Apenas SP é permitido")
    cep: str
    complemento: Optional[str] = None
    referencia: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v):
        if v.upper() != "SP":
            raise ValueError("Apenas endereços do estado de São Paulo (SP) são permitidos.")
        return v.upper()

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, v):
        if not re.match(r"^\d{5}-?\d{3}$", v):
            raise ValueError("CEP inválido! Use o formato 00000-000.")
        v = v.replace("-", "")
        return f"{v[:5]}-{v[5:]}"

class EnderecoCreate(EnderecoBase):
    pass

class EnderecoResponse(EnderecoBase):
    id: int
    user_id: int # <-- CORRIGIDO para int (para bater com o modelo Usuario)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# ====================================================================
# SCHEMAS DE ITEM (CARDÁPIO)
# ====================================================================

class ItemBase(BaseSchema):
    """Campos que o admin vai preencher para CRIAR um item"""
    nome: str
    preco: float = Field(..., gt=0) 
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    imagem_url: Optional[str] = None
    ativo: bool = True

class ItemCreate(ItemBase):
    """Schema usado pela rota de criação (é o que entra)"""
    pass

class ItemResponse(BaseSchema):
    """Schema de resposta (o que sai) - ATUALIZADO"""
    id: int
    restaurant_id: str
    nome: str
    preco: float
    descricao: Optional[str]
    categoria: Optional[str]
    imagem_url: Optional[str] 
    ativo: bool
    criado_em: datetime

# ====================================================================
# SCHEMAS DE PEDIDO (ORDER)
# ====================================================================

class PedidoItemResponse(BaseSchema):
    """Mostra um item que FOI comprado dentro de um pedido"""
    id: int
    item_id: int
    quantidade: int
    preco_unitario_pago: float

class OrderResponse(BaseSchema):
    """Resposta completa de um Pedido (mostra os itens dentro)"""
    id: int
    user_id: int 
    restaurant_id: str 
    status: OrderStatus
    total_price: float
    criado_em: datetime
    itens: List[PedidoItemResponse] = []

class CartItem(BaseModel):
    """Item individual do carrinho enviado pelo front-end"""
    item_id: int
    quantidade: int

class PedidoCreate(BaseModel):
    """O que o front-end envia para criar um pedido"""
    restaurante_id: str 
    endereco_id: int
    itens_do_carrinho: List[CartItem]

class OrderStatusUpdate(BaseModel):
    """Modelo para o admin atualizar o status"""
    status: OrderStatus 


# ====================================================================
# SCHEMAS DA SACOLA (CARRINHO) - (O QUE FALTAVA)
# ====================================================================

class SacolaItemBase(BaseSchema):
    """O que o frontend (consulta_restaurante) envia para a sacola."""
    item_id: int
    quantidade: int
    restaurant_id: str # O google_place_id
    
    # --- A CORREÇÃO ESTÁ AQUI ---
    # Adicionamos os campos que o frontend está enviando
    nome: str
    preco: float

class SacolaItemCreate(SacolaItemBase):
    """O 'molde' que a rota POST /sacola/{user_id} vai usar."""
    pass

class SacolaItemResponse(SacolaItemBase):
    """Como um item da sacola será retornado pela API."""
    # (É igual ao Base, mas podemos adicionar 'id' se o JSON salvar IDs)
    class Config:
        from_attributes = True

class SacolaResponse(BaseSchema):
    """Como a sacola inteira será retornada pela API."""
    id: int
    user_id: int
    total_price: float
    status: str
    
    # A API vai ler o JSON string e o Pydantic vai converter
    # em uma lista de SacolaItemResponse
    items: List[SacolaItemResponse] 

    class Config:
        from_attributes = True