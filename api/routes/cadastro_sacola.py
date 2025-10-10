from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.sacola_model import Sacola as SacolaDB

router = APIRouter(prefix="/api/sacola", tags=["Sacola"])

# Dependência para sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos Pydantic
class Item(BaseModel):
    product_id: int
    name: str
    price: float
    quantity: int

class SacolaCreate(BaseModel):
    user_id: int
    items: List[Item]

class SacolaResponse(BaseModel):
    id: int
    user_id: int
    items: List[Item]
    total_price: float
    status: str

    class Config:
        from_attributes = True  # Pydantic v2

# POST: criar sacola
@router.post("/", response_model=SacolaResponse, status_code=status.HTTP_201_CREATED)
def criar_sacola(sacola_data: SacolaCreate, db: Session = Depends(get_db)):
    if not sacola_data.items:
        raise HTTPException(status_code=400, detail="A sacola não pode estar vazia.")

    total_price = sum(item.price * item.quantity for item in sacola_data.items)

    nova_sacola = SacolaDB(
        user_id=sacola_data.user_id,
        items=[item.model_dump() for item in sacola_data.items],
        total_price=round(total_price, 2),
        status="aberta"
    )

    db.add(nova_sacola)
    db.commit()
    db.refresh(nova_sacola)
    return nova_sacola

# GET: listar todas as sacolas
@router.get("/", response_model=List[SacolaResponse])
def listar_sacolas(db: Session = Depends(get_db)):
    return db.query(SacolaDB).all()
