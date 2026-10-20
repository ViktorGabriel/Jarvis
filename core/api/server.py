import asyncio
import json
import logging
from typing import Any, Set
import websockets
from core.api.protocol import EventType, WSEvent, AgentState

logger = logging.getLogger("JarvisServer")

class JarvisServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[Any] = set()
        self.state: AgentState = AgentState.IDLE
        self.on_message_callback = None
        self._server = None

    @staticmethod
    def _is_ws_closed(ws: Any) -> bool:
        if hasattr(ws, "closed"):
            return bool(ws.closed)
        state = getattr(ws, "state", None)
        if state is not None and hasattr(state, "name"):
            return state.name in ("CLOSED", "CLOSING")
        return False

    async def register(self, ws: Any):
        self.clients.add(ws)
        logger.info(f"HUD conectado: {getattr(ws, 'remote_address', 'local')}")
        # Envia o estado atual assim que conecta
        await self.send_to(ws, EventType.STATE_UPDATE, {
            "state": self.state.value,
            "version": "1.0.0"
        })

    async def unregister(self, ws: Any):
        if ws in self.clients:
            self.clients.remove(ws)
            logger.info(f"HUD desconectado: {getattr(ws, 'remote_address', 'local')}")

    async def broadcast(self, event_type: EventType, data: dict):
        if not self.clients:
            return
        msg = json.dumps({"event": event_type.value, "data": data})
        to_remove = set()
        for ws in list(self.clients):
            if self._is_ws_closed(ws):
                to_remove.add(ws)
                continue
            try:
                await ws.send(msg)
            except Exception:
                to_remove.add(ws)
        for ws in to_remove:
            await self.unregister(ws)

    async def send_to(self, ws: Any, event_type: EventType, data: dict):
        msg = json.dumps({"event": event_type.value, "data": data})
        try:
            await ws.send(msg)
        except Exception:
            await self.unregister(ws)

    async def update_state(self, new_state: AgentState, detail: str = ""):
        self.state = new_state
        await self.broadcast(EventType.STATE_UPDATE, {
            "state": new_state.value,
            "detail": detail
        })

    async def _handler(self, ws: Any):
        await self.register(ws)
        try:
            async for raw_message in ws:
                try:
                    payload = json.loads(raw_message)
                    if self.on_message_callback:
                        await self.on_message_callback(payload)
                except Exception as e:
                    logger.error(f"Erro processando mensagem do HUD: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.warning(f"Conexão com HUD finalizada: {e}")
        finally:
            await self.unregister(ws)

    async def start(self):
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"Servidor J.A.R.V.I.S WebSocket ouvindo em ws://{self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("Servidor J.A.R.V.I.S WebSocket encerrado.")
