from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

# --- IMPORTS CORRIGIDOS ---
from src.database import get_db
# 1. Importar a classe 'Usuario' (em vez de 'usuarios' ou 'User')
from src.models.usuario import Usuario 
from src.security import get_password_hash
# ---------------------

# --- Schemas Pydantic (Modelos de Dados) ---
class UserCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: Annotated[str, Field(min_length=6)]

class UserResponse(BaseModel):
    id: int
    nome_completo: str
    email: EmailStr

    class Config:
        # 2. Corrigido de 'orm_mode = True' para o Pydantic V2
        from_attributes = True 

# --- API Router ---
router = APIRouter(
    prefix="/api/usuario",
    tags=["Usuário"]
)

# --- API Routes ---
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Cria um novo usuário no banco de dados."""
    
    # 3. Corrigido de 'User' para 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está em uso."
        )
    
    hashed_password = get_password_hash(user.senha) 
    
    # 4. Corrigido de 'User' para 'Usuario'
    new_user = Usuario(
        nome_completo=user.nome_completo,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=list[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 5. Corrigido de 'User' para 'Usuario'
    users = db.query(Usuario).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    # 6. Corrigido de 'User' para 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserCreate, db: Session = Depends(get_db)):
    # 7. Corrigido de 'User' para 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db_user.nome_completo = user_update.nome_completo
    db_user.email = user_update.email
    db_user.hashed_password = get_password_hash(user_update.senha)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # 8. Corrigido de 'User' para 'Usuario'
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(db_user)
    db.commit()
    return {"ok": True}