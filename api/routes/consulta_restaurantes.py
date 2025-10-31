import os
import requests
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
import asyncio 

# --- IMPORTAÇÕES DO BANCO DE DADOS (PostgreSQL/SQLAlchemy) ---
from sqlalchemy.orm import Session
from src.database import get_db 
from src.models import endereco 
from src.models import usuario 
from src import schemas  # <--- 1. IMPORTAÇÃO ADICIONADA

# --- Variáveis de Ambiente (Google API Key) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") 

# O objeto 'router' que será importado pelo main.py
router = APIRouter(
    tags=["Restaurantes"]
)

# --- ROTA DE CONSULTA DE ENDEREÇO (A CAUSA DO ERRO) ---
# (Estou assumindo que você tem uma rota como esta no arquivo)
@router.get("/endereco/{user_id}", response_model=schemas.EnderecoResponse) # <-- 2. CORRIGIDO
def consultar_endereco_do_usuario(user_id: str, db: Session = Depends(get_db)):
    """ Consulta o endereço de um usuário (exemplo). """
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido.")

    endereco_db = db.query(endereco.Endereco).filter(endereco.Endereco.user_id == user_id_int).first() 
    if not endereco_db:
        raise HTTPException(status_code=404, detail="Endereço não cadastrado.")
    return endereco_db


# --- FUNÇÃO HELPER: BUSCAR LOCALIZAÇÃO DO USUÁRIO (Versão PostgreSQL) ---
async def get_user_location(
    user_id: int, 
    db: Session 
) -> Dict[str, float]:
    """
    Busca a localização (lat/lng) do usuário no banco de dados PostgreSQL.
    """
    
    try:
        address = db.query(endereco.Endereco).filter(
    endereco.Endereco.user_id == str(user_id) # <--- CORREÇÃO AQUI
        ).first() 

        if not address:
             raise HTTPException(
                status_code=404, 
                detail="Localização do usuário não encontrada. Cadastre um endereço primeiro."
            )
        
        if not address.latitude or not address.longitude:
            raise HTTPException(
                status_code=404, 
                detail="O endereço cadastrado não possui latitude/longitude."
            )
            
        return {"lat": address.latitude, "lng": address.longitude} # Corrigido para latitude/longitude

    except HTTPException:
        raise 
    except Exception as e:
        print(f"Erro ao consultar o PostgreSQL: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Serviço de banco de dados (PostgreSQL) indisponível."
        )


# --- ROTA PRINCIPAL: CONSULTA RESTAURANTES PRÓXIMOS ---
@router.get("/nearby/{user_id}", response_model=List[Dict[str, Any]])
async def consulta_restaurantes_proximos(
    user_id: str, 
    search: Optional[str] = Query(None, description="Termo de busca (nome ou tipo de comida)"),
    db: Session = Depends(get_db) 
):
    """
    Busca restaurantes próximos à localização do usuário (do PostgreSQL) 
    usando a Google Places API.
    """
    
    # --- Passo 1: Converter ID e buscar localização ---
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido. Deve ser um número.")
        
    location = await get_user_location(user_id_int, db)

    # --- Passo 2: Lógica da Google Places API ---
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Chave da Google Places API (GOOGLE_PLACES_API_KEY) não configurada no servidor.")
    
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
        response = await asyncio.to_thread(requests.get, url, params=params)
        response.raise_for_status() 
        data = response.json()
        
        if data['status'] == 'OK' or data['status'] == 'ZERO_RESULTS':
            return data.get('results', [])
        else:
            raise HTTPException(status_code=400, detail=f"Erro na consulta à API do Google: {data.get('status')} - {data.get('error_message', '')}")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail="Serviço de consulta de restaurantes (Google Places) indisponível.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado no backend: {e}")
