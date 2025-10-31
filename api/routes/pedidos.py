from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, relationship
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, Enum

from src.database import get_db, Base # Importa Base e get_db
from pydantic import BaseModel
from typing import List, Optional

# ===================================================================
# 1. ENUM E MODELOS PYDANTIC (Requisição)
# ===================================================================

class OrderStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO_PARA_ENTREGA = "PRONTO_PARA_ENTREGA"
    EM_ROTA = "EM_ROTA"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"

class ItemCreate(BaseModel):
    id: int      # ID do *Produto*
    quantity: int

class AddressCreate(BaseModel):
    nomeDestinatario: str
    cep: str
    numero: str
    rua: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str

class OrderCreate(BaseModel):
    items: List[ItemCreate]
    total: float
    address: AddressCreate
    paymentMethod: str
    observations: Optional[str] = None
    changeFor: Optional[str] = None

# ===================================================================
# 2. MODELOS DE BANCO DE DADOS (SQLALCHEMY)
# ===================================================================

class OrderModel(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDENTE, nullable=False)
    total = Column(Float, nullable=False)
    paymentMethod = Column(String, nullable=False)
    # --- CAMPOS DUPLICADOS REMOVIDOS DAQUI ---
    observations = Column(Text, nullable=True)
    changeFor = Column(String, nullable=True) # Armazena "5000" (centavos)
    
    # Relação 1-para-1 com Endereço
    address = relationship("OrderAddressModel", back_populates="order", uselist=False, cascade="all, delete-orphan")
    
    # Relação 1-para-Muitos com Itens
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")

class OrderAddressModel(Base):
    __tablename__ = "order_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    nomeDestinatario = Column(String)
    cep = Column(String)
    numero = Column(String)
    rua = Column(String)
    complemento = Column(String, nullable=True)
    bairro = Column(String)
    cidade = Column(String)
    estado = Column(String)
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("OrderModel", back_populates="address")

class OrderItemModel(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False) # O ID do produto no seu catálogo
    quantity = Column(Integer, nullable=False)
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("OrderModel", back_populates="items")

# ===================================================================
# 3. MODELOS DE DADOS (PYDANTIC) - Resposta
# ===================================================================

class ItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    
    class Config:
        from_attributes = True

class AddressResponse(BaseModel):
    id: int
    nomeDestinatario: str
    rua: str
    numero: str
    
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    status: OrderStatus # <-- Já estava correto
    total: float
    paymentMethod: str
    address: AddressResponse
    items: List[ItemResponse]
    
    class Config:
        from_attributes = True

# ===================================================================
# 4. ROTEADOR E ENDPOINT DE CRIAÇÃO
# ===================================================================

router = APIRouter(
    prefix="/pedidos",  # Sem /api, conforme seu frontend
    tags=["Pedidos"]
)

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """
    Cria um novo pedido no banco de dados.
    """
    
    # Validação de Troco
    if order.paymentMethod == "DINHEIRO" and order.changeFor:
        try:
            troco_valor = int(order.changeFor) / 100
            if troco_valor < order.total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="O valor do troco não pode ser menor que o total do pedido."
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Formato inválido para o valor do troco."
            )
            
    # 1. Cria o Endereço
    db_address = OrderAddressModel(**order.address.model_dump())
    
    # 2. Cria os Itens
    db_items = [
        OrderItemModel(product_id=item.id, quantity=item.quantity) 
        for item in order.items
    ]
    
    # 3. Cria o Pedido principal
    db_order = OrderModel(
        total=order.total,
        paymentMethod=order.paymentMethod,
        observations=order.observations,
        changeFor=order.changeFor
        # O 'status' usará o 'default=OrderStatus.PENDENTE'
    )
    
    # 4. Associa o endereço e os itens ao pedido
    db_order.address = db_address
    db_order.items = db_items
    
    # 5. Salva no banco de dados
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar no banco: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível processar o pedido."
        )
        
    return db_order

# ===================================================================
# 5. ENDPOINTS DE CONSULTA (Cliente) - (ETAPA 2)
# ===================================================================

@router.get("/meus-pedidos", response_model=List[OrderResponse])
def get_my_orders(db: Session = Depends(get_db)):
    """
    (Versão Simplificada) Busca todos os pedidos.
    TODO: Adicionar autenticação para buscar apenas os pedidos
    do usuário logado (ex: filtrando por user_id).
    """
    # Ordena do mais novo para o mais antigo
    orders = db.query(OrderModel).order_by(OrderModel.id.desc()).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    """
    Busca um pedido específico pelo seu ID.
    TODO: Adicionar autenticação para garantir que o usuário
    logado é o dono deste pedido.
    """
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )
        
    return order