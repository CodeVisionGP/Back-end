from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), unique=True, nullable=False)
    nota = Column(Integer, nullable=False) # 1 a 5
    comentario = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamento
    pedido = relationship("OrderModel", backref="avaliacao")
