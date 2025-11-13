import os
import requests 
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.endereco import Endereco
from src import schemas # <-- Para usar o EnderecoResponse

# --- Variáveis de Ambiente (Google API Key) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# O objeto 'router' que será importado pelo main.py
router = APIRouter(
    tags=["Restaurantes"]
)

# --- FUNÇÃO HELPER: BUSCAR LOCALIZAÇÃO DO USUÁRIO ---
async def get_user_location(
    user_id: int,
    db: Session
) -> Dict[str, float]:
    """
    Busca a localização (lat/lng) do usuário no banco de dados.
    """
    
    try:
        # Busca o endereço pelo user_id
        # NOTE: Usamos int(user_id) na rota abaixo, por isso o filtro é seguro.
        address = db.query(Endereco).filter(
            Endereco.user_id == user_id 
        ).first()

        if not address or not address.latitude or not address.longitude:
             raise HTTPException(
                status_code=404,
                detail="Localização do usuário não encontrada. Cadastre um endereço primeiro."
            )
            
        return {"lat": address.latitude, "lng": address.longitude}

    except Exception as e:
        print(f"Erro ao consultar o PostgreSQL: {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviço de banco de dados indisponível."
        )


# --- ROTA PRINCIPAL: CONSULTA RESTAURANTES PRÓXIMOS ---
@router.get("/nearby/{user_id}", response_model=List[Dict[str, Any]])
async def consulta_restaurantes_proximos(
    user_id: str,
    search: Optional[str] = Query(None, description="Termo de busca (nome ou tipo de comida)"),
    db: Session = Depends(get_db)
):
    """
    Busca restaurantes próximos à localização do usuário usando a Google Places API.
    """
    
    # --- Passo 1: Converter ID e buscar localização ---
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido. Deve ser um número.")
        
    # Esta função faz a busca no DB
    location = await get_user_location(user_id_int, db)

    # --- Passo 2: Lógica da Google Places API ---
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Chave da Google Places API não configurada.")
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    keyword = search if search else 'comida'

    params = {
        'location': f"{location['lat']},{location['lng']}",
        'radius': 5000,
        'type': 'restaurant',
        'keyword': keyword,
        'key': GOOGLE_API_KEY
    }
    
    try:
        # Usa asyncio.to_thread para rodar a chamada síncrona de requests
        response = await asyncio.to_thread(requests.get, url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' or data['status'] == 'ZERO_RESULTS':
            return data.get('results', [])
        else:
            print(f"Erro do Google Places: {data.get('status')} - {data.get('error_message', '')}")
            raise HTTPException(status_code=400, detail=f"Erro na consulta à API do Google: {data.get('status')}")
            
    except requests.exceptions.RequestException as e:
        # Isto é o que geralmente causa o 503
        raise HTTPException(status_code=503, detail="Serviço de consulta de restaurantes (Google Places) indisponível.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado no backend: {e}")


# --- ROTA DE CONSULTA DE ENDEREÇO (A ROTA QUE O CHECKOUT CHAMA) ---
@router.get("/endereco/{user_id}", response_model=schemas.EnderecoResponse)
def consultar_endereco_do_usuario(user_id: int, db: Session = Depends(get_db)):
    """ Consulta o endereço de um usuário (exemplo). """
    
    endereco_db = db.query(Endereco).filter(Endereco.user_id == user_id).first()
    if not endereco_db:
        raise HTTPException(status_code=404, detail="Endereço não cadastrado.")
    return endereco_db