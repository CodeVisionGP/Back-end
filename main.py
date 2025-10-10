from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import cadastro_endereco, cadastro_usuario, cadastro_sacola, consulta_items

app = FastAPI(title="Backend Integrado")

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui todas as rotas
app.include_router(cadastro_endereco.router)
app.include_router(consulta_items.router)
app.include_router(cadastro_usuario.router)
app.include_router(cadastro_sacola.router)

@app.get("/")
async def root():
    return {"message": "Backend funcionando"}
