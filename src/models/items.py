from sqlalchemy import Column, Integer, String, Float, ForeignKey
from src.database import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    sacola_id = Column(Integer, ForeignKey("sacolas.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
