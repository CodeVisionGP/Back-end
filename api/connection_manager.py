from fastapi import WebSocket
from typing import List, Dict
from collections import defaultdict
import json

from api.routes.pedidos import OrderResponse # Reutilizaremos o modelo de resposta

class ConnectionManager:
    """
    Gerencia as conexões WebSocket ativas.
    
    A estrutura é um dicionário onde:
    - Chave (Key): order_id (int)
    - Valor (Value): Lista de WebSockets [WebSocket, WebSocket, ...]
    
    Isso permite que múltiplas conexões (ex: celular e laptop)
    ouçam o mesmo pedido.
    """
    def __init__(self):
        # defaultdict(list) cria automaticamente uma lista vazia
        # se tentarmos acessar um order_id que ainda não existe.
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, order_id: int):
        """Aceita e armazena uma nova conexão."""
        await websocket.accept()
        self.active_connections[order_id].append(websocket)
        print(f"Conexão [Order ID: {order_id}] - Conexão estabelecida.")

    def disconnect(self, websocket: WebSocket, order_id: int):
        """Remove uma conexão da lista."""
        self.active_connections[order_id].remove(websocket)
        print(f"Conexão [Order ID: {order_id}] - Conexão encerrada.")

    async def broadcast_to_order(self, order_id: int, data: dict):
        """
        Envia uma mensagem JSON para todas as conexões
        que estão ouvindo um order_id específico.
        """
        print(f"Broadcast [Order ID: {order_id}] - Enviando dados: {data['status']}")
        
        # Pega a lista de conexões para este pedido
        connections = self.active_connections.get(order_id, [])
        
        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                # Lida com conexões que podem ter caído
                print(f"Erro ao enviar para websocket: {e}")


# Cria uma instância única (Singleton) que será usada em toda a aplicação
manager = ConnectionManager()