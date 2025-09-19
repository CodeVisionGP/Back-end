# main.py
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field



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


db_in_memory: List[EnderecoDB] = []


app = FastAPI(
    title="Cadastro de Endereço",
    version="1.0.0"
)


origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/enderecos", response_model=EnderecoDB, status_code=status.HTTP_201_CREATED)
async def criar_endereco(endereco: EnderecoSchema):
  
    print(f"Recebido novo endereço: {endereco.dict()}")
    
    
    novo_endereco = EnderecoDB(**endereco.dict())
    
   
    db_in_memory.append(novo_endereco)
    
    print(f"Endereço salvo com sucesso! ID: {novo_endereco.id}")
    return novo_endereco

@app.get("/api/enderecos", response_model=List[EnderecoDB])
async def listar_enderecos():
   
    return db_in_memory


@app.get("/")
async def root():
    return {"message": "funcionando"}