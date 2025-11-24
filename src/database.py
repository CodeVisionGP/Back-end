# CORREÇÃO FINAL: Removed import of EnderecoModel to break the circular dependency.
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# --- CONEXÃO USANDO VARIÁVEIS DE AMBIENTE ---
SQLALCHEMY_DATABASE_URL = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "senha"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    db=os.getenv("DB_NAME", "ifome")
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# função para fornecer sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
