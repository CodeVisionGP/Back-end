import os
import requests 
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.endereco import Endereco
from src import schemas 

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
        address = db.query(Endereco).filter(
            Endereco.user_id == user_id 
        ).first()

        if not address or not address.latitude or not address.longitude:
             # Se não achar endereço ou coordenadas, lança erro 404 específico
             raise HTTPException(
                status_code=404,
                detail="Localização do usuário não encontrada. Cadastre um endereço primeiro."
            )
            
        return {"lat": address.latitude, "lng": address.longitude}

    except HTTPException:
        raise # Re-levanta exceções HTTP já tratadas
    except Exception as e:
        print(f"Erro ao consultar o PostgreSQL: {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviço de banco de dados indisponível."
        )


# --- ROTA PRINCIPAL: CONSULTA RESTAURANTES PRÓXIMOS ---
# Esta é a rota que estava dando 404. Ela deve estar acessível em:
# /api/restaurantes/nearby/{user_id}
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
        print("ERRO: GOOGLE_PLACES_API_KEY não encontrada no .env")
        raise HTTPException(status_code=500, detail="Configuração de API inválida no servidor.")
    
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
        # Usa asyncio.to_thread para rodar a chamada síncrona de requests sem bloquear o servidor
        response = await asyncio.to_thread(requests.get, url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') in ['OK', 'ZERO_RESULTS']:
            return data.get('results', [])
        else:
            print(f"Erro do Google Places: {data.get('status')} - {data.get('error_message', '')}")
            # Se a chave do Google for inválida ou houver erro de cota, retorna 503 ou 400
            raise HTTPException(status_code=503, detail=f"Erro externo na busca de restaurantes: {data.get('status')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com Google: {e}")
        raise HTTPException(status_code=503, detail="Serviço de busca de restaurantes indisponível temporariamente.")
    except Exception as e:
        print(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")


# --- ROTA DE CONSULTA DE ENDEREÇO ---
@router.get("/endereco/{user_id}")
def consultar_endereco_do_usuario(user_id: int, db: Session = Depends(get_db)):
    """ Consulta o endereço de um usuário para preencher o checkout. """
    
    endereco_db = db.query(Endereco).filter(Endereco.user_id == user_id).first()
    if not endereco_db:
        raise HTTPException(status_code=404, detail="Endereço não cadastrado.")
    
    # Retorna um dict manual para garantir que o ID seja enviado
    return {
        "id": endereco_db.id,
        "user_id": endereco_db.user_id,
        "rua": endereco_db.rua,
        "numero": endereco_db.numero,
        "bairro": endereco_db.bairro,
        "cidade": endereco_db.cidade,
        "estado": endereco_db.estado,
        "cep": endereco_db.cep,
        "complemento": endereco_db.complemento,
        "referencia": endereco_db.referencia,
        "latitude": endereco_db.latitude,
        "longitude": endereco_db.longitude
    }