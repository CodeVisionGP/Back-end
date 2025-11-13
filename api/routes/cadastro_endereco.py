import os
import re
import asyncio 
import requests 
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importar dependências do Firebase Admin
from firebase_admin import credentials, initialize_app, firestore, _apps

# --- Nossas Importações Locais Corrigidas ---
from src.database import get_db
from src.models.endereco import Endereco  # <-- IMPORTA O MODELO
from src import schemas                     # <-- IMPORTA OS SCHEMAS


# --- Variáveis de Ambiente ---
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") 
APP_ID = os.getenv("__APP_ID", "default-app-id")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")


# --- Inicialização Condicional do Firebase Admin ---
# (Seu código de inicialização do Firebase)
db_firestore = None
if not _apps:
    initialized_successfully = False
    service_account_path = None
    if FIREBASE_CREDENTIALS_PATH:
        service_account_path = os.path.abspath(FIREBASE_CREDENTIALS_PATH.strip('"')) 

    if service_account_path and os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            initialize_app(cred)
            initialized_successfully = True
        except Exception:
            pass
            
    if not initialized_successfully:
        try:
            cred = credentials.ApplicationDefault() 
            initialize_app(cred)
        except Exception as e:
            print(f"Aviso: Falha ao inicializar o Firebase Admin. Salvamento no Firestore desabilitado: {e}")
            
try:
    db_firestore = firestore.client()
except Exception:
    db_firestore = None


router = APIRouter(
    prefix="/api/endereco",
    tags=["Endereço"]
)

# --- FUNÇÃO DE GEOCODIFICAÇÃO AUTOMÁTICA ---
def geocode_address(endereco_completo: str) -> Dict[str, float]:
    """Converte um endereço de texto em Lat/Lng usando o Google Geocoding API."""
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Chave da Google Places API não configurada no servidor.")
        
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': endereco_completo,
        'key': GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and len(data['results']) > 0:
            location = data['results'][0]['geometry']['location']
            return {"lat": location['lat'], "lng": location['lng']}
        else:
            print(f"Geocodificação falhou: {data.get('error_message', data['status'])}")
            raise HTTPException(status_code=400, detail="Não foi possível encontrar as coordenadas para o endereço fornecido.")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com Geocoding API: {e}")
        raise HTTPException(status_code=503, detail="Serviço de geocodificação indisponível.")


# --- Função auxiliar para salvar no Firestore ---
async def save_to_firestore(uid: str, data: Dict[str, Any]):
    """Salva as coordenadas no Firestore para o Front-end."""
    if not db_firestore:
        return 
    
    try:
        doc_path = db_firestore.document(f"artifacts/{APP_ID}/users/{uid}/user_settings/default_address")
        doc_path.set({
            "lat": data['latitude'],
            "lng": data['longitude'],
            "rua": data['rua'],
        })
    except Exception as e:
        print(f"Erro ao salvar endereço no Firestore: {e}")


# --- ROTA PRINCIPAL: CADASTRO COM GEOCODIFICAÇÃO ---
@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def cadastrar_endereco(
    user_id: int, # <-- CORREÇÃO: Mudado de str para int
    endereco: schemas.EnderecoCreate,
    db: Session = Depends(get_db)
):
    """Cadastra um endereço, geocodifica (preenche lat/lng automaticamente) e salva no DB/Firestore."""
    
    # 1. Monta o endereço completo para Geocodificação
    endereco_completo = (
        f"{endereco.rua}, {endereco.numero}, {endereco.bairro}, "
        f"{endereco.cidade}, {endereco.estado}, {endereco.cep}"
    )
    
    # 2. Geocodifica o endereço (converte para Lat/Lng)
    try:
        coordenadas = geocode_address(endereco_completo)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no serviço de geocodificação: {e}")

    # 3. Verifica se já existe (SQLAlchemy)
    # (A query agora compara int com int, o que está correto)
    existente = db.query(Endereco).filter(Endereco.user_id == user_id).first() 
    
    # 4. Cria o objeto de dados final
    endereco_data = endereco.model_dump()
    endereco_data['latitude'] = coordenadas['lat']
    endereco_data['longitude'] = coordenadas['lng']
    
    if existente:
        # Atualiza o endereço existente
        for key, value in endereco_data.items():
            setattr(existente, key, value)
        db.commit()
        db.refresh(existente)
        mensagem = "Endereço atualizado com sucesso!"
    else:
        # Cadastra novo endereço
        novo_endereco = Endereco(user_id=user_id, **endereco_data)
        db.add(novo_endereco)
        db.commit()
        db.refresh(novo_endereco)
        mensagem = "Endereço cadastrado com sucesso!"

    # 5. Sincroniza a localização para o Front-end (Firestore)
    firestore_data = {
        "latitude": coordenadas['lat'],
        "longitude": coordenadas['lng'],
        "rua": endereco.rua,
    }
    # CORREÇÃO: O Firestore precisa de um 'uid' (string)
    asyncio.create_task(save_to_firestore(str(user_id), firestore_data))
    
    return {
        "mensagem": mensagem, 
        "coordenadas": coordenadas
    }


# --- ROTA DE CONSULTA ---
@router.get("/{user_id}", response_model=schemas.EnderecoResponse) 
def consultar_endereco(
    user_id: int, # <-- CORREÇÃO: Mudado de str para int
    db: Session = Depends(get_db)
):
    """Consulta endereço de um usuário específico, retornando também lat/lng."""
    
    # Busca no banco usando o MODELO
    endereco_db = db.query(Endereco).filter(Endereco.user_id == user_id).first() 
    
    if not endereco_db:
        raise HTTPException(status_code=404, detail="Usuário ainda não possui endereço cadastrado.")
    
    return endereco_db