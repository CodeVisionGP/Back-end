from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

# --- IMPORTANT IMPORTS ---
# This assumes your other code is now organized correctly
from src.database import get_db
from src.models.usuario import User
from src.security import verify_password

# --- Pydantic Schema for Login ---
class UserLogin(BaseModel):
    email: EmailStr
    senha: str

# --- API Router ---
router = APIRouter(
    prefix="/api/auth",  # Let's give it a clean prefix like /api/auth
    tags=["Autenticação"]
)

# --- JSON Login Route (This is the "new method") ---
@router.post("/login", status_code=status.HTTP_200_OK)
def api_login_user(form_data: UserLogin, db: Session = Depends(get_db)):
    """
    Handles user login for API clients (like Next.js).
    Receives JSON and returns JSON.
    """
    
    # 1. Find the user by email
    db_user = db.query(User).filter(User.email == form_data.email).first()

    # 2. Check if user exists and if passwords match
    if not db_user or not verify_password(form_data.senha, db_user.hashed_password):
        # If user not found or password is wrong, raise an error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Success! Return a JSON message.
    return {"message": "Login successful", "user": db_user.nome_completo}