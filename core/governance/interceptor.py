import asyncio
import logging
import uuid
from typing import Dict, Optional, Callable, Any
from core.governance.policy import GovernancePolicy, RiskLevel
from core.api.protocol import EventType

logger = logging.getLogger("SafetyInterceptor")

class SafetyTicket:
    def __init__(self, action_type: str, description: str, command: str, risk_reason: str):
        self.id = str(uuid.uuid4())[:8]
        self.action_type = action_type
        self.description = description
        self.command = command
        self.risk_reason = risk_reason
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self.future: asyncio.Future[bool] = loop.create_future()

class SafetyInterceptor:
    def __init__(self, broadcast_fn: Optional[Callable[[EventType, dict], Any]] = None):
        self.pending_tickets: Dict[str, SafetyTicket] = {}
        self.broadcast_fn = broadcast_fn

    def set_broadcaster(self, fn: Callable[[EventType, dict], Any]):
        self.broadcast_fn = fn

    async def guard_command(self, command: str, description: str = "") -> bool:
        risk, reason = GovernancePolicy.evaluate_command(command)
        if risk == RiskLevel.SAFE:
            return True

        # Travamento preventivo
        ticket = SafetyTicket(
            action_type="command_execution",
            description=description or "Execução de comando restrito no terminal",
            command=command,
            risk_reason=reason
        )
        self.pending_tickets[ticket.id] = ticket

        # Notifica o HUD imediatamente
        if self.broadcast_fn:
            await self.broadcast_fn(EventType.SAFETY_APPROVAL_REQUEST, {
                "ticket_id": ticket.id,
                "action_type": ticket.action_type,
                "description": ticket.description,
                "command": ticket.command,
                "risk_reason": ticket.risk_reason,
            })

        # Aguarda decisão visual ou por voz com timeout de 120 segundos
        try:
            approved = await asyncio.wait_for(ticket.future, timeout=120.0)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout de autorização de governança para ticket [{ticket.id}]. Bloqueado preventivamente.")
            approved = False
        finally:
            self.pending_tickets.pop(ticket.id, None)
        return approved

    def resolve_ticket(self, ticket_id: str, approved: bool):
        if ticket_id in self.pending_tickets:
            ticket = self.pending_tickets[ticket_id]
            if not ticket.future.done():
                ticket.future.set_result(approved)
