from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from src.database import Base # Importe a Base do seu arquivo database.py

class Item(Base):
    """
    Esta é a representação da sua tabela 'items' no banco de dados.
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    # NOTE: O restaurant_id é o place_id do Google, que é uma string
    restaurant_id = Column(String, index=True, nullable=False) 
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    descricao = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    imagem_url = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Adicione relacionamentos se necessário
    # ex: owner = relationship("Restaurante", back_populates="items")
