# src/models/usuario.py
# (Este é o conteúdo CORRETO para este arquivo)

from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base # 👈 Ajuste o import do Base se necessário

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Você pode adicionar relacionamentos aqui depois, se precisar
    # ex: endereco = relationship("Endereco", back_populates="dono")