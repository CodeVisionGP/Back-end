from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship # Adicionado para futuros relacionamentos
from src.database import Base 

class Usuario(Base): # Mudei o nome da classe para 'Usuario' por consistência
    """
    Modelo de Usuário CORRIGIDO.
    A tabela agora se chama 'usuarios' (português).
    """
    __tablename__ = "usuarios" # <-- CORREÇÃO 1: 'users' -> 'usuarios'

    id = Column(Integer, primary_key=True, index=True) # <-- O ID é um Integer
    nome_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # --- Relacionamentos ---
    # Adicionei os 'back_populates' para o SQLAlchemy entender as ligações
    
    # Um usuário pode ter muitos endereços
    enderecos = relationship("Endereco", back_populates="dono")
    
    # Um usuário pode ter muitos pedidos
    pedidos = relationship("OrderModel", back_populates="usuario")