from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.items import Item

router = APIRouter(
    prefix="/api/restaurants",
    tags=["Consulta de Items"]
)

@router.get("/{restaurant_id}/items")
def get_items_for_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.restaurant_id == restaurant_id).all()
    if not items:
        raise HTTPException(status_code=404, detail="Nenhum item encontrado para este restaurante.")
    return items
