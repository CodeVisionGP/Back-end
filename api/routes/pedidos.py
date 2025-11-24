import os
import requests 
import asyncio
import random # Para gerar o código
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import get_db
from src.models.pedidos import OrderModel, PedidoItem, OrderStatus, TipoEntrega
from src.models.items import Item as ItemModel
from src.models.usuario import Usuario 
from src.models.endereco import Endereco
from src import schemas

EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://localhost:3001/api/nf/enviar")

async def enviar_nf_microsservico(
    destinatario: str, 
    order_id: int, 
    nome_cliente: str,
    endereco_cliente: str,
    itens: list,
    total: float,
    tipo_entrega: str,
    horario_entrega: str,
    codigo_entrega: str # <--- Novo parâmetro
):
    if not EMAIL_SERVICE_URL or destinatario == 'placeholder@phone.placeholder':
        return

    itens_payload = []
    for item in itens:
        nome_prato = "Item"
        if hasattr(item, 'item') and item.item:
             nome_prato = item.item.nome
        itens_payload.append({
            "nome": nome_prato,
            "quantidade": item.quantidade,
            "preco_unitario": item.preco_unitario_pago
        })

    info_entrega = f"Tipo: {tipo_entrega}"
    if horario_entrega: info_entrega += f" (Agendado: {horario_entrega})"

    # Adiciona o código ao corpo do e-mail
    corpo_email = (
        f"Olá {nome_cliente}!\n\n"
        f"Seu pedido foi confirmado.\n{info_entrega}\n\n"
        f"🔐 CÓDIGO DE ENTREGA: {codigo_entrega}\n"
        f"(Informe este código ao entregador apenas ao receber o pedido)\n\n"
        f"Segue anexa a Nota Fiscal."
    )

    payload = {
        "to": destinatario,
        "orderId": order_id,
        "subject": f"Pedido #{order_id} Confirmado (Cód: {codigo_entrega})",
        "bodyText": corpo_email,
        "clienteNome": nome_cliente,
        "clienteEndereco": endereco_cliente,
        "total": total,
        "itens": itens_payload,
        "fileName": f"NF_Pedido_{order_id}.pdf",
        "pdfBase64": "" 
    }

    try:
        await asyncio.to_thread(requests.post, EMAIL_SERVICE_URL, json=payload, timeout=10)
        print(f"E-mail enviado com Código de Entrega!")
    except Exception as e:
        print(f"ERRO ao enviar e-mail: {e}")

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos (Cliente)"])

@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return db_order

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(pedido_data: schemas.PedidoCreate, db: Session = Depends(get_db)):
    user_id_mock = 2 
    db_usuario = db.query(Usuario).filter(Usuario.id == user_id_mock).first()
    if not db_usuario: raise HTTPException(status_code=404, detail="Usuário não autenticado.")
    db_endereco = db.query(Endereco).filter(Endereco.id == pedido_data.endereco_id).first()
    endereco_str = f"{db_endereco.rua}, {db_endereco.numero}" if db_endereco else "N/A"
    
    itens_para_salvar_no_db = []
    preco_total_calculado = 0.0
    taxa_entrega_extra = 5.00 if pedido_data.tipo_entrega == TipoEntrega.RAPIDA else 0.00

    for item_carrinho in pedido_data.itens_do_carrinho:
        item_db = db.query(ItemModel).filter(ItemModel.id == item_carrinho.item_id).first()
        if not item_db: raise HTTPException(status_code=404, detail=f"Item {item_carrinho.item_id} não encontrado.")
        preco_unitario_real = item_db.preco
        preco_total_calculado += (preco_unitario_real * item_carrinho.quantidade)
        novo_item_pedido = PedidoItem(item_id=item_db.id, quantidade=item_carrinho.quantidade, preco_unitario_pago=preco_unitario_real)
        novo_item_pedido.item = item_db 
        itens_para_salvar_no_db.append(novo_item_pedido)

    if not itens_para_salvar_no_db: raise HTTPException(status_code=400, detail="Carrinho vazio.")
    preco_total_calculado += taxa_entrega_extra

    # --- GERAÇÃO DO CÓDIGO ---
    # Gera um número aleatório de 0000 a 9999
    codigo_gerado = f"{random.randint(0, 9999):04d}"

    novo_pedido = OrderModel(
        user_id=db_usuario.id, 
        status=OrderStatus.PENDENTE,
        total_price=preco_total_calculado,
        restaurant_id=pedido_data.restaurante_id, 
        endereco_id=pedido_data.endereco_id,
        tipo_entrega=pedido_data.tipo_entrega,
        horario_entrega=pedido_data.horario_entrega,
        # Salva o código
        codigo_entrega=codigo_gerado 
    )
    novo_pedido.itens = itens_para_salvar_no_db
    
    try:
        db.add(novo_pedido) 
        db.commit()
        db.refresh(novo_pedido)
        
        asyncio.create_task(enviar_nf_microsservico(
            destinatario=db_usuario.email, 
            order_id=novo_pedido.id,
            nome_cliente=db_usuario.nome_completo,
            endereco_cliente=endereco_str,
            itens=itens_para_salvar_no_db,
            total=preco_total_calculado,
            tipo_entrega=pedido_data.tipo_entrega.value,
            horario_entrega=pedido_data.horario_entrega,
            codigo_entrega=codigo_gerado
        ))
        
        return novo_pedido
    except Exception as e:
        db.rollback()
        print(f"ERRO AO SALVAR: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {e}")

# --- NOVA ROTA: VALIDAR ENTREGA (USADA PELO ENTREGADOR) ---
@router.post("/{order_id}/entregar")
def validar_entrega(order_id: int, dados: schemas.ValidacaoEntrega, db: Session = Depends(get_db)):
    """
    Rota para o entregador validar o código. Se correto, finaliza o pedido.
    """
    pedido = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status == OrderStatus.CONCLUIDO:
        return {"mensagem": "Pedido já foi entregue anteriormente."}

    # Verifica o código
    if pedido.codigo_entrega == dados.codigo:
        pedido.status = OrderStatus.CONCLUIDO
        db.commit()
        return {"mensagem": "Código correto! Pedido CONCLUÍDO com sucesso."}
    else:
        raise HTTPException(status_code=400, detail="Código de entrega incorreto!")
    


@router.get("/", response_model=List[schemas.OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    """
    Lista todos os pedidos do usuário logado (mockado como 2).
    """
    user_id_mock = 2 # Mesmo mock usado no create_order
    
    # Busca pedidos do usuário, ordenados por data (mais recente primeiro)
    # Usa joinedload para trazer os itens junto, se necessário no schema
    orders = db.query(OrderModel).filter(
        OrderModel.user_id == user_id_mock
    ).order_by(OrderModel.criado_em.desc()).all()
    
    return orders