import os
import re
import asyncio 
import requests 
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import Session

# Importar dependências do Firebase Admin
from firebase_admin import credentials, initialize_app, firestore, _apps # Inclui _apps

# Importações de módulos locais (Ajuste o caminho se necessário)
# Assumindo que 'src.database' está no mesmo nível de 'api'
from src.database import Base, SessionLocal 


# --- Variáveis de Ambiente ---
# CORRIGIDO: Agora usa a chave de API correta para Geocodificação (AIzaSy...)
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") 
# O ID do aplicativo para uso no Firestore (regra de segurança)
APP_ID = os.getenv("__APP_ID", "default-app-id")
# Caminho opcional para o arquivo de credenciais JSON do Service Account
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")


# --- Inicialização Condicional do Firebase Admin (Refatorada) ---
db_firestore = None

# A inicialização é feita APENAS se nenhum app do Firebase existir
if not _apps:
    
    initialized_successfully = False
    
    # Tentativa de inicialização com Service Account JSON
    service_account_path = None
    if FIREBASE_CREDENTIALS_PATH:
        service_account_path = os.path.abspath(FIREBASE_CREDENTIALS_PATH.strip('"')) 

    if service_account_path and os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            initialize_app(cred)
            initialized_successfully = True
        except Exception:
            # Falha silenciosa em caso de JSON inválido ou erro de leitura
            pass
        
    # Tentativa de inicialização com Application Default Credentials (ADC), se a anterior falhou
    if not initialized_successfully:
        try:
            cred = credentials.ApplicationDefault() 
            initialize_app(cred)
        except Exception as e:
            # O print é mantido fora do bloco try/except principal para evitar capturar erros de inicialização
            print(f"Aviso: Falha ao inicializar o Firebase Admin. Salvamento no Firestore desabilitado: {e}")
            
try:
    # Se o app foi inicializado com sucesso (em qualquer módulo ou neste), criamos o cliente.
    # Se houver um erro de inicialização, db_firestore será None.
    db_firestore = firestore.client()
except Exception:
    # Captura caso o initialize_app tenha falhado em ambos os caminhos
    db_firestore = None


router = APIRouter(
    prefix="/api/endereco",
    tags=["Endereço"]
)

# --- FUNÇÃO DE GEOCODIFICAÇÃO AUTOMÁTICA ---
def geocode_address(endereco_completo: str) -> Dict[str, float]:
    """Converte um endereço de texto em Lat/Lng usando o Google Geocoding API."""
    # CORRIGIDO: Agora usa GOOGLE_PLACES_API_KEY
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


# Modelo SQLAlchemy (Com Lat/Lng)
class EnderecoModel(Base):
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False) # Deve ser compatível com o UID (String)
    rua = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    bairro = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    cep = Column(String, nullable=False)
    complemento = Column(String, nullable=True)
    referencia = Column(String, nullable=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


# Modelo de dados (entrada do usuário)
class Endereco(BaseModel):
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str = Field(..., description="Apenas SP é permitido")
    cep: str
    complemento: Optional[str] = None
    referencia: Optional[str] = None
    
    # Validação de estado
    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v):
        if v.upper() != "SP":
            raise ValueError("Apenas endereços do estado de São Paulo (SP) são permitidos.")
        return v.upper()

    # Validação de CEP
    @field_validator("cep")
    @classmethod
    def validar_cep(cls, v):
        if not re.match(r"^\d{5}-?\d{3}$", v):
            raise ValueError("CEP inválido! Use o formato 00000-000.")
        v = v.replace("-", "")
        return f"{v[:5]}-{v[5:]}"


# Dependência para sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função auxiliar para salvar no Firestore
async def save_to_firestore(uid: str, data: Dict[str, Any]):
    """Salva as coordenadas no Firestore, que é a fonte de dados primária do Front-end."""
    if not db_firestore:
        return 
    
    try:
        # Caminho seguindo a regra de segurança de dados privados: 
        # artifacts/{appId}/users/{userId}/user_settings/default_address
        doc_path = db_firestore.document(f"artifacts/{APP_ID}/users/{uid}/user_settings/default_address")
        
        # Salva o Lat e Lng que o Front-end de consulta espera
        doc_path.set({
            "lat": data['latitude'],
            "lng": data['longitude'],
            "rua": data['rua'],
        })
    except Exception as e:
        print(f"Erro ao salvar endereço no Firestore: {e}")


# --- ROTA PRINCIPAL: CADASTRO COM GEOCODIFICAÇÃO ---
@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def cadastrar_endereco(user_id: str, endereco: Endereco, db: Session = Depends(get_db)):
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
    existente = db.query(EnderecoModel).filter(EnderecoModel.user_id == user_id).first()
    
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
        novo_endereco = EnderecoModel(user_id=user_id, **endereco_data)
        db.add(novo_endereco)
        db.commit()
        db.refresh(novo_endereco)
        mensagem = "Endereço cadastrado com sucesso!"

    # 5. Sincroniza a localização para o Front-end (Firestore) em segundo plano
    firestore_data = {
        "latitude": coordenadas['lat'],
        "longitude": coordenadas['lng'],
        "rua": endereco.rua,
    }
    # A verificação 'if not db_firestore' já está na função save_to_firestore, 
    # então o código será executado apenas se o db estiver ativo.
    asyncio.create_task(save_to_firestore(user_id, firestore_data))
    
    return {
        "mensagem": mensagem, 
        "coordenadas": coordenadas
    }


# --- ROTA DE CONSULTA ---
@router.get("/{user_id}")
def consultar_endereco(user_id: str, db: Session = Depends(get_db)):
    """Consulta endereço de um usuário específico, retornando também lat/lng."""
    endereco = db.query(EnderecoModel).filter(EnderecoModel.user_id == user_id).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Usuário ainda não possui endereço cadastrado.")
    return endereco
