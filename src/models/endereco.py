from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Endereco(Base):
    """
    Modelo de Endereço CORRIGIDO.
    """
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    
    # FK para Usuario (mantido como Integer, que é o tipo correto)
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

    # Ligação com o Usuário
    dono = relationship("Usuario", back_populates="enderecos")
    
    # 🛑 CORREÇÃO FINAL: RELACIONAMENTO COM PEDIDOS 
    # O OrderModel tem 'endereco = relationship("Endereco", back_populates="pedidos")'
    # Esta linha completa o ciclo:
    pedidos = relationship("OrderModel", back_populates="endereco")