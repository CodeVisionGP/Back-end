from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
import re

# Cria o router com prefixo e tag
router = APIRouter(
    prefix="/api/endereco",
    tags=["Endereço"]
)

# Simula um "banco de dados" na memória
usuarios = {}


# Modelo de dados (entrada e validação)
class Endereco(BaseModel):
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str = Field(..., description="Apenas SP é permitido")
    cep: str
    complemento: str | None = None
    referencia: str | None = None

    @field_validator("estado")
    def validar_estado(cls, v):
        if v.upper() != "SP":
            raise ValueError("Apenas endereços do estado de São Paulo (SP) são permitidos.")
        return v.upper()

    @field_validator("cep")
    def validar_cep(cls, v):
        if not re.match(r"^\d{5}-?\d{3}$", v):
            raise ValueError("CEP inválido! Use o formato 00000-000.")
        v = v.replace("-", "")
        return f"{v[:5]}-{v[5:]}"


@router.post("/{user_id}", status_code=201)
def cadastrar_endereco(user_id: int, endereco: Endereco):
    """Cadastra um endereço novo para o usuário."""
    if user_id in usuarios:
        raise HTTPException(status_code=409, detail="Usuário já possui endereço cadastrado.")
    
    usuarios[user_id] = endereco.model_dump()
    return {"mensagem": "Endereço cadastrado com sucesso!", "endereco": usuarios[user_id]}


@router.get("/{user_id}")
def consultar_endereco(user_id: int):
    """Retorna o endereço do usuário, se existir."""
    if user_id not in usuarios:
        raise HTTPException(status_code=404, detail="Usuário ainda não possui endereço cadastrado.")
    return {"user_id": user_id, "endereco": usuarios[user_id]}
