# ARQUIVO FINAL: api/routes/relatorios.py (Corrigido para corresponder ao Histórico)

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String, Text, desc, Integer 
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel

# --- Importações de Modelos ---
from src.database import get_db
from src.models.pedidos import OrderModel, PedidoItem, OrderStatus 
from src.models.restaurante import RestaurantModel 
from src.models.avaliacao import Avaliacao 
from src.models.items import Item 

# --- SCHEMAS DE RESPOSTA ---
# (Manter Schemas aqui para evitar conflitos de importação)
class RelatorioPedidosPorPeriodo(BaseModel): 
    data_inicio_periodo: date
    data_fim_periodo: date
    total_pedidos: int = 0
    faturamento_total: float = 0.0
    ticket_medio: float = 0.0
    restaurante_mais_pedidos: str = "N/A"
    class Config: from_attributes = True

class RestauranteMaisVendasResponse(BaseModel):
    rank: int
    restaurante: str
    n_pedidos: int
    faturamento: float
    avaliacao_media: float
    class Config: from_attributes = True

class ProdutoMaisVendidoResponse(BaseModel):
    rank: int
    produto: str
    quantidade: int
    valor_faturado: float
    class Config: from_attributes = True

class DailyMetricResponse(BaseModel):
    data: date
    faturamento: float
    class Config:
        from_attributes = True

# --- Configuração do Router ---
router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])

# -----------------------------------------------------
# ROTA 1: Pedidos por Período (DADOS AGREGADOS)
# -----------------------------------------------------

@router.get("/pedidos_por_periodo", response_model=RelatorioPedidosPorPeriodo)
def get_relatorio_pedidos_por_periodo(
    data_inicio: date = Query(..., description="Data de início do período"),
    data_fim: date = Query(..., description="Data de fim do período"),
    db: Session = Depends(get_db)
):
    # 🛑 FILTRO DE STATUS REMOVIDO: Agora inclui todos os pedidos no período
    query_filtro = db.query(OrderModel).filter(
        func.date(OrderModel.criado_em).between(data_inicio, data_fim) 
        # Removido: OrderModel.status == OrderStatus.PENDENTE
    )

    metricas = query_filtro.with_entities(
        func.count(OrderModel.id).label('total_pedidos'),
        func.sum(OrderModel.total_price).label('faturamento_total'),
    ).first()

    total_pedidos = metricas.total_pedidos if metricas.total_pedidos else 0
    faturamento_total = metricas.faturamento_total if metricas.faturamento_total else 0.0

    if total_pedidos == 0:
        return RelatorioPedidosPorPeriodo(
            data_inicio_periodo=data_inicio, data_fim_periodo=data_fim
        )
    
    ticket_medio = faturamento_total / total_pedidos
    
    # ✅ JOIN: Corrigido e funcional
    top_restaurante = query_filtro.join(
        RestaurantModel, 
        RestaurantModel.id.cast(Text) == OrderModel.restaurant_id.cast(Text)
    ).with_entities(
        RestaurantModel.name,
        func.count(OrderModel.id).label('contagem_pedidos')
    ).group_by(RestaurantModel.name).order_by(
        func.count(OrderModel.id).desc()
    ).first()
    
    nome_top_restaurante = top_restaurante.name if top_restaurante else "N/A"

    return RelatorioPedidosPorPeriodo(
        data_inicio_periodo=data_inicio, data_fim_periodo=data_fim, total_pedidos=total_pedidos,
        faturamento_total=round(faturamento_total, 2), ticket_medio=round(ticket_medio, 2),
        restaurante_mais_pedidos=nome_top_restaurante
    )


# -----------------------------------------------------
# ROTA 2: Restaurantes com Mais Vendas
# -----------------------------------------------------

@router.get("/restaurantes_mais_vendas", response_model=List[RestauranteMaisVendasResponse])
def get_relatorio_restaurantes(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    top_n: int = Query(5, description="Número de restaurantes no ranking"),
    db: Session = Depends(get_db)
):
    query = db.query(
        RestaurantModel.name.label('restaurante'),
        func.count(OrderModel.id).label('n_pedidos'),
        func.sum(OrderModel.total_price).label('faturamento'),
        func.avg(Avaliacao.nota).label('avaliacao_media')
    ).join(
        OrderModel, 
        RestaurantModel.id.cast(Text) == OrderModel.restaurant_id.cast(Text)
    ).outerjoin(
        Avaliacao, OrderModel.id == Avaliacao.pedido_id 
    ) # 🛑 FILTRO DE STATUS REMOVIDO AQUI

    if data_inicio and data_fim:
        query = query.filter(func.date(OrderModel.criado_em).between(data_inicio, data_fim))

    resultados = query.group_by(
        RestaurantModel.name
    ).order_by(
        desc(func.sum(OrderModel.total_price))
    ).limit(top_n).all()

    relatorio = []
    for i, res in enumerate(resultados):
        relatorio.append(RestauranteMaisVendasResponse(
            rank=i + 1, restaurante=res.restaurante, n_pedidos=res.n_pedidos,
            faturamento=round(res.faturamento if res.faturamento else 0.0, 2),
            avaliacao_media=round(res.avaliacao_media if res.avaliacao_media else 0.0, 1)
        ))
        
    return relatorio


# -----------------------------------------------------
# ROTA 3: Produtos Mais Vendidos
# -----------------------------------------------------

@router.get("/produtos_mais_vendidos", response_model=List[ProdutoMaisVendidoResponse])
def get_relatorio_produtos(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    top_n: int = Query(5, description="Número de produtos no ranking"),
    db: Session = Depends(get_db)
):
    query = db.query(
        func.sum(PedidoItem.quantidade).label('quantidade'),
        func.sum(PedidoItem.quantidade * PedidoItem.preco_unitario_pago).label('valor_faturado'),
        Item.nome.label('produto') 
    ).join(
        OrderModel, PedidoItem.order_id == OrderModel.id
    ).join(
        Item, PedidoItem.item_id == Item.id 
    ) # 🛑 FILTRO DE STATUS REMOVIDO AQUI

    if data_inicio and data_fim:
        query = query.filter(func.date(OrderModel.criado_em).between(data_inicio, data_fim))

    resultados = query.group_by(
        Item.nome
    ).order_by(
        desc(func.sum(PedidoItem.quantidade))
    ).limit(top_n).all()

    relatorio = []
    for i, res in enumerate(resultados):
        relatorio.append(ProdutoMaisVendidoResponse(
            rank=i + 1, produto=res.produto, quantidade=int(res.quantidade),
            valor_faturado=round(res.valor_faturado if res.valor_faturado else 0.0, 2)
        ))
        
    return relatorio


# -----------------------------------------------------
# ROTA 4: Pedidos por Dia (Série Temporal para Gráfico)
# -----------------------------------------------------

@router.get("/pedidos_por_dia", response_model=List[DailyMetricResponse])
def get_pedidos_por_dia(
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    # 🛑 FILTRO DE STATUS REMOVIDO AQUI
    resultados = db.query(
        func.date(OrderModel.criado_em).label('data'),
        func.sum(OrderModel.total_price).label('faturamento')
    ).filter(
        func.date(OrderModel.criado_em).between(data_inicio, data_fim)
    ).group_by(
        func.date(OrderModel.criado_em)
    ).order_by(
        func.date(OrderModel.criado_em)
    ).all()
    
    # ... (Restante da função)
    relatorio = []
    for res in resultados:
        relatorio.append(DailyMetricResponse(
            data=res.data,
            faturamento=round(res.faturamento, 2) if res.faturamento else 0.0
        ))
        
    return relatorio