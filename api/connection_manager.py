from fastapi import WebSocket
from typing import List, Dict
from collections import defaultdict
import json

# Removemos imports desnecessários para evitar erros circulares
# Apenas gerenciamos a conexão aqui.

class ConnectionManager:
    """
    Gerencia as conexões WebSocket ativas.
    """
    def __init__(self):
        # Dicionário que guarda uma lista de sockets para cada order_id
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, order_id: int):
        """Aceita a conexão e guarda na lista."""
        await websocket.accept()
        self.active_connections[order_id].append(websocket)
        print(f"🔌 WebSocket Conectado! [Pedido #{order_id}] - Total conexões: {len(self.active_connections[order_id])}")

    def disconnect(self, websocket: WebSocket, order_id: int):
        """Remove a conexão da lista."""
        if order_id in self.active_connections:
            if websocket in self.active_connections[order_id]:
                self.active_connections[order_id].remove(websocket)
                print(f"🔌 WebSocket Desconectado [Pedido #{order_id}]")
            
            # Limpa a chave se não houver mais ninguém ouvindo
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def broadcast_to_order(self, order_id: int, data: dict):
        """Envia dados para todos conectados naquele pedido."""
        if order_id in self.active_connections:
            print(f"📢 Enviando atualização para Pedido #{order_id}")
            connections = self.active_connections[order_id]
            
            for connection in list(connections):
                try:
                    await connection.send_json(data)
                except Exception as e:
                    print(f"Erro ao enviar via socket: {e}")
                    self.disconnect(connection, order_id)

# Instância única para ser usada em todo o app
manager = ConnectionManager()