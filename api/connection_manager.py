from fastapi import WebSocket
from typing import List, Dict
from collections import defaultdict
import json

# --- A CORREÇÃO ESTÁ AQUI ---
# Importe 'OrderResponse' do seu arquivo de schemas (src/schemas.py),
# e não do arquivo de rotas (api/routes/pedidos.py).
from src.schemas import OrderResponse 

class ConnectionManager:
    """
    Gerencia as conexões WebSocket ativas.
    """
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, order_id: int):
        """Aceita e armazena uma nova conexão."""
        await websocket.accept()
        self.active_connections[order_id].append(websocket)
        print(f"Conexão [Order ID: {order_id}] - Conexão estabelecida.")

    def disconnect(self, websocket: WebSocket, order_id: int):
        """Remove uma conexão da lista."""
        try:
            self.active_connections[order_id].remove(websocket)
            print(f"Conexão [Order ID: {order_id}] - Conexão encerrada.")
            if not self.active_connections[order_id]:
                # Limpa a chave se for a última conexão
                del self.active_connections[order_id]
        except ValueError:
            # Acontece se a conexão já foi removida
            pass 

    async def broadcast_to_order(self, order_id: int, data: dict):
        """
        Envia uma mensagem JSON para todas as conexões
        que estão ouvindo um order_id específico.
        """
        print(f"Broadcast [Order ID: {order_id}] - Enviando status: {data.get('status')}")
        
        # Pega a lista de conexões para este pedido
        connections = self.active_connections.get(order_id, [])
        
        # Usamos list(connections) para fazer uma cópia.
        # Isso evita erros se um cliente desconectar durante o broadcast.
        for connection in list(connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                # Lida com conexões que podem ter caído
                print(f"Erro ao enviar para websocket: {e}. Removendo conexão.")
                self.disconnect(connection, order_id)


# Cria uma instância única (Singleton) que será usada em toda a aplicação
manager = ConnectionManager()