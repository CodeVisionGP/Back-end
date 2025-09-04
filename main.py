from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext

# Configuração do banco
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuração de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo User
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependência para sessão
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funções auxiliares
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

# ------------------------
# ROTAS CRUD DO USUÁRIO
# ------------------------

# CREATE (Cadastrar usuário)
@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    hashed_pw = hash_password(password)
    new_user = User(email=email, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "Usuário cadastrado com sucesso", "user_id": new_user.id}

# READ (Login)
@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"msg": "Login realizado com sucesso", "user_id": user.id}

# UPDATE (Atualizar senha)
@app.put("/update-password")
def update_password(email: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.password = hash_password(new_password)
    db.commit()
    return {"msg": "Senha atualizada com sucesso"}

# DELETE (Excluir conta)
@app.delete("/delete-user")
def delete_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()
    return {"msg": "Usuário excluído com sucesso"}
