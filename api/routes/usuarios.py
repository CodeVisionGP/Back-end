# Em: api/routes/usuarios.py (ARQUIVO NOVO)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# --- Imports no estilo 'src' que funciona no seu projeto ---
from src.database import get_db
from src.models.usuario import User
from src.models.endereco import Endereco # 👈 Importe o modelo de Endereco

# ---------------------------------------------------------


# Crie o router com o prefixo /usuarios
# É ESTE PREFIXO que vai bater com a URL do frontend
router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuarios"]
)


@router.get(
    "/{user_id}/endereco",
    summary="Busca o endereço de um usuário específico"
)
async def get_user_address(user_id: int, db: Session = Depends(get_db)):
    
    # 1. Busca o usuário (para pegar o nome)
    usuario_db = db.query(User).filter(User.id == user_id).first()

    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuário não encontrado"
        )

    # 2. Busca o endereço
    endereco_db = db.query(Endereco).filter(Endereco.user_id == user_id).first()

    if not endereco_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Endereço não encontrado para este usuário"
        )

    # 3. Combina os dados e retorna EXATAMENTE o que o frontend espera
    return {
        "nome_destinatario": usuario_db.nome_completo, 
        "cep": endereco_db.cep,
        "rua": endereco_db.rua,
        "numero": endereco_db.numero,
        "bairro": endereco_db.bairro,
        "cidade": endereco_db.cidade,
        "estado": endereco_db.estado,
        "complemento": endereco_db.complemento
    }