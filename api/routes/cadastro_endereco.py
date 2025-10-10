from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, relationship

from src.database import Base, SessionLocal  # importa do seu database.py
import re

router = APIRouter(
    prefix="/api/endereco",
    tags=["Endereço"]
)

# Modelo SQLAlchemy
class EnderecoModel(Base):
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    rua = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    bairro = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    cep = Column(String, nullable=False)
    complemento = Column(String, nullable=True)
    referencia = Column(String, nullable=True)

    # se quiser no futuro:
    # user = relationship("User", back_populates="endereco")

# Cria tabela se não existir
Base.metadata.create_all(bind=SessionLocal().bind)


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


# Dependência para sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
def cadastrar_endereco(user_id: int, endereco: Endereco, db: Session = Depends(get_db)):
    """Cadastra um endereço novo para o usuário (salva no banco)."""
    # verifica se já existe
    existente = db.query(EnderecoModel).filter(EnderecoModel.user_id == user_id).first()
    if existente:
        raise HTTPException(status_code=409, detail="Usuário já possui endereço cadastrado.")
    
    novo_endereco = EnderecoModel(user_id=user_id, **endereco.model_dump())
    db.add(novo_endereco)
    db.commit()
    db.refresh(novo_endereco)
    return {"mensagem": "Endereço cadastrado com sucesso!", "endereco": endereco.model_dump()}


@router.get("/{user_id}")
def consultar_endereco(user_id: int, db: Session = Depends(get_db)):
    """Consulta endereço de um usuário específico."""
    endereco = db.query(EnderecoModel).filter(EnderecoModel.user_id == user_id).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Usuário ainda não possui endereço cadastrado.")
    return endereco
