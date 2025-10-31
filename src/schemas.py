import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

# Config base para Pydantic (substitui o 'orm_mode')
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True # Novo padrão do Pydantic V2

# --- Schemas de Endereço ---
# (Os schemas que já tínhamos do 'cadastro_endereco')

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
    user_id: str
    latitude: float
    longitude: float


# --- Schemas de Item ---
# (Esta é a parte que estava faltando e causando o erro)

class ItemResponse(BaseSchema):
    id: int
    restaurant_id: str
    nome: str
    preco: float
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ativo: bool
    criado_em: datetime

