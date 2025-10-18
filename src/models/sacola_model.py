from sqlalchemy import Column, Integer, Float, String, JSON
from src.database import Base

class Sacola(Base):
    __tablename__ = "sacolas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    items = Column(JSON, nullable=False)       # Lista de itens
    total_price = Column(Float, nullable=False)
    status = Column(String(20), default="aberta")
