import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base 
# Note: As classes 'Usuario' e 'Endereco' devem ser acessíveis via import
# Ex: from .usuario import Usuario
# Ex: from .endereco import Endereco

class OrderStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    EM_PREPARO = "EM_PREPARO"
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"

class TipoEntrega(str, enum.Enum):
    NORMAL = "NORMAL"
    RAPIDA = "RAPIDA"
    AGENDADA = "AGENDADA"

class OrderModel(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False) 
    
    # Foreign Key para o ID do Google Places (STRING)
    restaurant_id = Column(String, ForeignKey("restaurant.id"), index=True, nullable=False) 
    
    endereco_id = Column(Integer, ForeignKey("enderecos.id"), nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.PENDENTE)
    tipo_entrega = Column(SqlEnum(TipoEntrega), default=TipoEntrega.NORMAL)
    horario_entrega = Column(String, nullable=True)
    codigo_entrega = Column(String, nullable=True) 
    observacoes = Column(String, nullable=True) # Novo campo de observações
    criado_em = Column(DateTime, default=datetime.utcnow)

    # RELACIONAMENTOS (Corrigidos e Completos)
    usuario = relationship("Usuario", back_populates="pedidos") 
    itens = relationship("PedidoItem", back_populates="order", cascade="all, delete-orphan")
    endereco = relationship("Endereco", back_populates="pedidos")
    restaurant = relationship("RestaurantModel", back_populates="pedidos")

class PedidoItem(Base):
    __tablename__ = "pedido_itens"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("pedidos.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantidade = Column(Integer, nullable=False)
    preco_unitario_pago = Column(Float, nullable=False)
    order = relationship("OrderModel", back_populates="itens")
    item = relationship("Item")