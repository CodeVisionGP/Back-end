# main.py

import bcrypt
from typing import Annotated  # <--- ADICIONADO para a validação
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
# 'constr' foi trocado por 'Field'
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base  # <--- CORRIGIDO o import

# --- 1. Configuração do Banco de Dados (SQLite) ---
DATABASE_URL = "sqlite:///./ifome_clone.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. Modelo de Dados (Tabela de Usuários) ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

# Cria a tabela no banco de dados, se não existir
Base.metadata.create_all(bind=engine)

# --- 3. Schemas (Validação de Dados com Pydantic) ---
# Schema para criação de usuário (o que a API recebe)
class UserCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    # <--- CORRIGIDO: Validação da senha usando Annotated e Field
    senha: Annotated[str, Field(min_length=6)]

# Schema para exibir o usuário (o que a API retorna, sem a senha)
class UserResponse(BaseModel):
    id: int
    nome_completo: str
    email: EmailStr

    class Config:
        orm_mode = True

# --- 4. Funções de Segurança (Hashing de Senha) ---
def get_password_hash(password: str) -> str:
    """Cria o hash de uma senha."""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# --- 5. Dependência do Banco de Dados ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 6. Inicialização do FastAPI ---
app = FastAPI(
    title="API iFome Clone",
    description="API para o CRUD de usuários.",
    version="1.0.0"
)

# Configuração do CORS para permitir que o frontend acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 7. Endpoints da API (Rotas) ---

# CREATE - Rota para criar um novo usuário
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está em uso."
        )
    
    hashed_password = get_password_hash(user.senha)
    new_user = User(
        nome_completo=user.nome_completo,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# READ - Rota para obter uma lista de todos os usuários
@app.get("/users/", response_model=list[UserResponse], tags=["Users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

# READ - Rota para obter um usuário específico pelo ID
@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    return db_user

# UPDATE - Rota para atualizar os dados de um usuário
@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def update_user(user_id: int, user_update: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db_user.nome_completo = user_update.nome_completo
    db_user.email = user_update.email
    db_user.hashed_password = get_password_hash(user_update.senha)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# DELETE - Rota para deletar um usuário
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(db_user)
    db.commit()
    return {"ok": True}