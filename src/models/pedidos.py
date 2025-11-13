import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime

# Importe sua Base do database
from src.database import Base 
# Importe o modelo de Item
from .items import Item 
# Importe o modelo de Usuario
from .usuario import Usuario

# (A linha de importação circular foi removida daqui)

# Enum de Status
class OrderStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    EM_PREPARO = "EM_PREPARO"
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"

class OrderModel(Base):
    """
    O "cabeçalho" do pedido.
    """
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    
    # 'Integer' para bater com o 'usuario.id'
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False) 
    
    restaurant_id = Column(String, index=True, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.PENDENTE)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # --- Relacionamentos ---
    itens = relationship(
        "PedidoItem", 
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    # Ligação inversa com o Usuário
    usuario = relationship("Usuario", back_populates="pedidos")

class PedidoItem(Base):
    """
    Item dentro do pedido.
    """
    __tablename__ = "pedido_itens"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("pedidos.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantidade = Column(Integer, nullable=False)
    preco_unitario_pago = Column(Float, nullable=False)
    
    # --- Relacionamentos ---
    order = relationship("OrderModel", back_populates="itens")
    item = relationship("Item")