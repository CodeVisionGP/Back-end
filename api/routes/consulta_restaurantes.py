import os
import requests
from typing import Dict, Any, List, Optional # Importado Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query # Importado Query
import asyncio 

# Importar dependências do Firebase Admin para ler a localização
from firebase_admin import credentials, initialize_app, firestore, get_app, _apps 

# --- Variáveis de Ambiente e Configuração (omitidas por brevidade) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") 
APP_ID = os.getenv("__APP_ID", "default-app-id")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

# --- Inicialização Condicional do Firebase Admin (omitida por brevidade) ---
db_firestore = None
try:
    # Verifica se o app padrão JÁ ESTÁ inicializado
    if not _apps: 
        
        service_account_path = None
        if FIREBASE_CREDENTIALS_PATH:
            service_account_path = os.path.abspath(FIREBASE_CREDENTIALS_PATH.strip('"')) 
            # ... lógica de inicialização de credenciais ...
            try:
                cred = credentials.Certificate(service_account_path)
                initialize_app(cred)
                # ...
            except FileNotFoundError:
                # ...
                pass
            except Exception:
                # ...
                pass

        if not get_app(name="[DEFAULT]"): # Verifica se já inicializou
            cred = credentials.ApplicationDefault() 
            initialize_app(cred)

    db_firestore = firestore.client()
except Exception as e:
    db_firestore = None

# O objeto 'router' que será importado pelo main.py
router = APIRouter(
    tags=["Restaurantes"]
)

# --- FUNÇÃO HELPER: BUSCAR LOCALIZAÇÃO DO USUÁRIO (omitida por brevidade) ---
async def get_user_location(user_id: str) -> Dict[str, float]:
    if not db_firestore:
        raise HTTPException(
            status_code=503,
            detail="Serviço de banco de dados indisponível (Firestore não inicializado)."
        )
    
    try:
        doc_path = f"artifacts/{APP_ID}/users/{user_id}/user_settings/default_address"
        doc_ref = db_firestore.document(doc_path)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404, 
                detail="Localização do usuário não encontrada. Cadastre um endereço primeiro."
            )
        
        data = doc.to_dict()
        return {"lat": data.get('lat'), "lng": data.get('lng')}

    except HTTPException:
        raise
    except Exception as e:
        # Erros internos como API do Firestore desativada
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar a localização do usuário: {e}")


# --- ROTA PRINCIPAL: CONSULTA RESTAURANTES PRÓXIMOS ---
@router.get("/nearby/{user_id}", response_model=List[Dict[str, Any]])
async def consulta_restaurantes_proximos(
    user_id: str, 
    # NOVO: Parâmetro de busca opcional do frontend
    search: Optional[str] = Query(None, description="Termo de busca (nome ou tipo de comida)"),
    # Dependência de localização assíncrona
    location: Dict[str, float] = Depends(get_user_location),
):
    """
    Busca restaurantes próximos à localização do usuário usando a Google Places API.
    A localização é lida do Firestore.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Chave da Google Places API (GOOGLE_PLACES_API_KEY) não configurada no servidor.")
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    # --- LÓGICA DO FILTRO ---
    # Define a palavra-chave. Se o termo de busca estiver vazio, usa 'comida' como fallback.
    keyword = search if search else 'comida'
    # -----------------------

    params = {
        'location': f"{location['lat']},{location['lng']}",
        'radius': 5000, 
        'type': 'restaurant', 
        'keyword': keyword, # <--- USANDO O TERMO DE BUSCA/FILTRO
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
        raise HTTPException(status_code=503, detail="Serviço de consulta de restaurantes indisponível.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado no backend: {e}")
