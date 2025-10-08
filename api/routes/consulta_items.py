from fastapi import APIRouter, HTTPException
import asyncio

router = APIRouter(
    prefix="/api/restaurants",
    tags=["Consulta de Items"]
)

# Mock de itens
mock_items = [
    {"id": 101, "restaurantId": 1, "name": "Pizza Margherita", "description": "Molho de tomate fresco, mussarela de búfala e manjericão.", "price": 45.50, "image": "https://placehold.co/600x400/f43f5e/white?text=Pizza"},
    {"id": 102, "restaurantId": 1, "name": "Lasanha à Bolonhesa", "description": "Massa fresca com ragu de carne e muito queijo.", "price": 52.00, "image": "https://placehold.co/600x400/ef4444/white?text=Lasanha"},
    {"id": 103, "restaurantId": 1, "name": "Ravioli de Espinafre", "description": "Massa recheada com espinafre e ricota ao molho branco.", "price": 48.90, "image": "https://placehold.co/600x400/f87171/white?text=Ravioli"},
    
    {"id": 201, "restaurantId": 2, "name": "Combinado Salmão (20pç)", "description": "Sashimi, niguiri e uramaki de salmão fresco.", "price": 75.00, "image": "https://placehold.co/600x400/ec4899/white?text=Combinado"},
    {"id": 202, "restaurantId": 2, "name": "Hot Roll (8pç)", "description": "Sushi empanado e frito com cream cheese e salmão.", "price": 28.00, "image": "https://placehold.co/600x400/f472b6/white?text=Hot+Roll"},
    {"id": 203, "restaurantId": 2, "name": "Yakisoba de Frango", "description": "Macarrão oriental com frango e legumes selecionados.", "price": 38.50, "image": "https://placehold.co/600x400/f0abfc/white?text=Yakisoba"},
    
    {"id": 301, "restaurantId": 3, "name": "Burger Duplo Bacon", "description": "Dois hambúrgueres, queijo cheddar, bacon e molho especial.", "price": 35.90, "image": "https://placehold.co/600x400/8b5cf6/white?text=Burger"},
]

# Rota para consultar itens por restaurante
@router.get("/{restaurant_id}/items")
async def get_items_for_restaurant(restaurant_id: int):
    items_for_restaurant = [item for item in mock_items if item["restaurantId"] == restaurant_id]
    
    # Simula tempo de resposta
    await asyncio.sleep(0.5)
    
    if items_for_restaurant:
        return items_for_restaurant
    else:
        raise HTTPException(status_code=404, detail="Nenhum item encontrado para este restaurante.")
