import React from 'react';
import { ShieldAlert, Check, X, Terminal } from 'lucide-react';
import { SafetyApprovalRequest } from '../types';

interface ApprovalModalProps {
  request: SafetyApprovalRequest | null;
  onDecision: (ticketId: string, approved: boolean) => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({ request, onDecision }) => {
  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="w-full max-w-xl bg-jarvis-bg/95 border-2 border-jarvis-alert shadow-hud-alert rounded-lg p-6 relative overflow-hidden">
        {/* Linha de escaneamento de alerta */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-jarvis-alert to-transparent animate-pulse" />

        <div className="flex items-center space-x-3 text-jarvis-alert mb-4">
          <ShieldAlert className="w-8 h-8 animate-bounce" />
          <div>
            <h2 className="text-xl font-hud font-bold tracking-widest uppercase">
              Travamento Preventivo de Segurança
            </h2>
            <p className="text-xs text-jarvis-alert/80 font-mono">
              PROTOCOLO DE CONFIRMAÇÃO CRÍTICA OBRIGATÓRIA • TICKET #{request.ticket_id}
            </p>
          </div>
        </div>

        <div className="space-y-3 mb-6 font-mono text-sm">
          <div className="bg-jarvis-card p-3 rounded border border-jarvis-alert/30">
            <span className="text-xs text-gray-400 block mb-1 uppercase tracking-wider">Motivo do Risco:</span>
            <p className="text-jarvis-alert font-semibold">{request.risk_reason}</p>
          </div>

          <div className="bg-black/60 p-3 rounded border border-jarvis-border">
            <div className="flex items-center space-x-2 text-xs text-jarvis-cyan mb-2">
              <Terminal className="w-4 h-4" />
              <span>COMANDO A SER EXECUTADO NO TERMINAL:</span>
            </div>
            <code className="text-white bg-black/80 p-2 block rounded overflow-x-auto text-xs font-mono border border-white/10">
              {request.command}
            </code>
          </div>
        </div>

        <div className="flex space-x-4">
          <button
            onClick={() => onDecision(request.ticket_id, false)}
            className="flex-1 flex items-center justify-center space-x-2 py-3 px-4 bg-red-950/40 hover:bg-red-900/60 text-red-400 border border-red-500/50 rounded font-hud font-bold tracking-wider transition-all duration-200"
          >
            <X className="w-5 h-5" />
            <span>CANCELAR OPERAÇÃO</span>
          </button>

          <button
            onClick={() => onDecision(request.ticket_id, true)}
            className="flex-1 flex items-center justify-center space-x-2 py-3 px-4 bg-emerald-950/40 hover:bg-emerald-800/60 text-emerald-400 border border-emerald-500/60 rounded font-hud font-bold tracking-wider shadow-lg hover:shadow-emerald-500/30 transition-all duration-200"
          >
            <Check className="w-5 h-5" />
            <span>AUTORIZAR EXECUÇÃO</span>
          </button>
        </div>
      </div>
    </div>
  );
};
