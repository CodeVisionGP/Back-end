from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Endereco(Base):
    """
    Modelo de Endereço CORRIGIDO.
    """
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    
    # --- CORREÇÃO 3: TIPO DO USER_ID ---
    # 'String' -> 'Integer' para bater com o 'usuario.id'
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    rua = Column(String)
    numero = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    estado = Column(String)
    cep = Column(String)
    complemento = Column(String, nullable=True)
    referencia = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Ligação inversa com o Usuário
    dono = relationship("Usuario", back_populates="enderecos")