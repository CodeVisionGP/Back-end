# ARQUIVO: src/models/restaurante.py

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base 

class RestaurantModel(Base):
    __tablename__ = "restaurant" 

    # ID como String (VARCHAR) é crucial
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True) 
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    is_open = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pedidos = relationship("OrderModel", back_populates="restaurant")