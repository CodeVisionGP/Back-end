import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/enderecos",
    tags=["Cadastro de Endereço"]
)

# Schemas
class EnderecoSchema(BaseModel):
    cep: str
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str

class EnderecoDB(EnderecoSchema):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# Banco de dados em memória
db_in_memory: List[EnderecoDB] = []

# Rotas
@router.post("/", response_model=EnderecoDB, status_code=status.HTTP_201_CREATED)
async def criar_endereco(endereco: EnderecoSchema):
    print(f"Recebido novo endereço: {endereco.dict()}")
    
    novo_endereco = EnderecoDB(**endereco.dict())
    db_in_memory.append(novo_endereco)
    
    print(f"Endereço salvo com sucesso! ID: {novo_endereco.id}")
    return novo_endereco

@router.get("/", response_model=List[EnderecoDB])
async def listar_enderecos():
    return db_in_memory
