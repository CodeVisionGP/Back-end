from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.avaliacao import Avaliacao
from src.models.pedidos import OrderModel
from src import schemas

router = APIRouter(
    prefix="/api/avaliacoes",
    tags=["Avaliações"]
)

# ROTA 1: CRIAR AVALIAÇÃO (A que você já tinha)
@router.post("/", response_model=schemas.AvaliacaoResponse, status_code=status.HTTP_201_CREATED)
def criar_avaliacao(
    avaliacao: schemas.AvaliacaoCreate,
    db: Session = Depends(get_db)
):
    # 1. Verifica se o pedido existe
    pedido = db.query(OrderModel).filter(OrderModel.id == avaliacao.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    # 2. Verifica se já foi avaliado
    ja_avaliado = db.query(Avaliacao).filter(Avaliacao.pedido_id == avaliacao.pedido_id).first()
    if ja_avaliado:
        raise HTTPException(status_code=400, detail="Este pedido já foi avaliado.")

    # 3. Salva a avaliação
    nova_avaliacao = Avaliacao(
        pedido_id=avaliacao.pedido_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario
    )
    
    db.add(nova_avaliacao)
    db.commit()
    db.refresh(nova_avaliacao)
    
    return nova_avaliacao


# ROTA 2: CONSULTAR SE JÁ EXISTE (Nova - Necessária para o Front-end)
@router.get("/pedido/{pedido_id}", response_model=schemas.AvaliacaoResponse)
def obter_avaliacao_por_pedido(
    pedido_id: int, 
    db: Session = Depends(get_db)
):
    # Busca a avaliação filtrando pelo ID do pedido
    avaliacao = db.query(Avaliacao).filter(Avaliacao.pedido_id == pedido_id).first()
    
    # Se não encontrar, retorna erro 404
    # O Front-end usa esse erro 404 para saber que PODE exibir o formulário
    if not avaliacao:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada para este pedido.")
        
    return avaliacao