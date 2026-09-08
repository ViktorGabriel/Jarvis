import React, { useEffect, useRef, useState } from 'react';
import { ShieldAlert, Check, X, Terminal, Mic, Keyboard } from 'lucide-react';
import { SafetyApprovalRequest } from '../types';

interface ApprovalModalProps {
  request: SafetyApprovalRequest | null;
  onDecision: (ticketId: string, approved: boolean) => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({ request, onDecision }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const [voiceStatus, setVoiceStatus] = useState<string>('Ouvindo comandos: "autorizado" ou "cancelar"');
  const [isVoiceListening, setIsVoiceListening] = useState<boolean>(false);

  // 1. Auto-foco imediato ao abrir o modal
  useEffect(() => {
    if (request) {
      modalRef.current?.focus();
    }
  }, [request]);

  // 2. Atalhos de Teclado: [Enter] para Autorizar, [Esc] para Cancelar
  useEffect(() => {
    if (!request) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        onDecision(request.ticket_id, true);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onDecision(request.ticket_id, false);
      }
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [request, onDecision]);

  // 3. Listener para Comandos de Voz de Confirmação (Web Speech API)
  useEffect(() => {
    if (!request) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceStatus('Reconhecimento por voz não suportado neste navegador');
      return;
    }

    let recognition: any = null;
    try {
      recognition = new SpeechRecognition();
      recognition.lang = 'pt-BR';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsVoiceListening(true);
        setVoiceStatus('Microfone ativo: diga "autorizado" ou "cancelar"');
      };

      recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          console.log('[Governança] Voz capturada:', transcript);

          // Gatilhos afirmativos
          const approveTriggers = ['autorizado', 'pode executar', 'confirmar', 'confirmado', 'autorizar', 'executar', 'pode rodar', 'aprovar'];
          if (approveTriggers.some((t) => transcript.includes(t))) {
            setVoiceStatus('Comando vocal reconhecido: AUTORIZADO');
            recognition.stop();
            onDecision(request.ticket_id, true);
            return;
          }

          // Gatilhos negativos
          const rejectTriggers = ['cancelar', 'cancelado', 'abortar', 'abortado', 'não', 'nao', 'recusar', 'parar'];
          if (rejectTriggers.some((t) => transcript.includes(t))) {
            setVoiceStatus('Comando vocal reconhecido: CANCELADO');
            recognition.stop();
            onDecision(request.ticket_id, false);
            return;
          }
        }
      };

      recognition.onerror = () => {
        setIsVoiceListening(false);
      };

      recognition.onend = () => {
        setIsVoiceListening(false);
      };

      recognition.start();
    } catch (err) {
      console.warn('[Governança] Falha ao iniciar reconhecimento de voz no modal:', err);
    }

    return () => {
      if (recognition) {
        try {
          recognition.stop();
        } catch (_) {}
      }
    };
  }, [request, onDecision]);

  if (!request) return null;

  return (
    <div
      ref={modalRef}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-2xl p-4 outline-none"
    >
      <div className="w-full max-w-xl bg-jarvis-bg/95 border-2 border-jarvis-alert shadow-hud-alert rounded-xl p-6 relative overflow-hidden">
        {/* Linha de escaneamento holográfica de alerta */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-jarvis-alert to-transparent animate-pulse" />

        <div className="flex items-center space-x-3 text-jarvis-alert mb-4">
          <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-500/50 animate-bounce">
            <ShieldAlert className="w-7 h-7 text-jarvis-alert" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-hud font-bold tracking-widest uppercase text-jarvis-alert">
                Travamento Preventivo de Segurança
              </h2>
              <span className="text-[10px] font-mono font-bold bg-red-950/80 text-red-300 px-2 py-0.5 rounded border border-red-500/40">
                TICKET #{request.ticket_id}
              </span>
            </div>
            <p className="text-xs text-jarvis-alert/80 font-mono">
              PROTOCOLO DE CONFIRMAÇÃO CRÍTICA OBRIGATÓRIA
            </p>
          </div>
        </div>

        <div className="space-y-3 mb-5 font-mono text-xs">
          {/* Motivo do Risco */}
          <div className="bg-jarvis-card p-3 rounded-lg border border-jarvis-alert/30">
            <span className="text-[10px] text-gray-400 block mb-1 uppercase tracking-wider font-hud">
              Motivo do Risco de Segurança:
            </span>
            <p className="text-jarvis-alert font-semibold leading-relaxed">{request.risk_reason}</p>
          </div>

          {/* Comando Terminal */}
          <div className="bg-black/70 p-3 rounded-lg border border-jarvis-border">
            <div className="flex items-center justify-between text-xs text-jarvis-cyan mb-2 font-hud font-bold">
              <span className="flex items-center space-x-1.5">
                <Terminal className="w-4 h-4" />
                <span>COMANDO A SER EXECUTADO NO TERMINAL:</span>
              </span>
              <span className="text-[10px] text-gray-400 font-mono">{request.action_type}</span>
            </div>
            <code className="text-white bg-black/90 p-2.5 block rounded overflow-x-auto text-xs font-mono border border-white/10 text-emerald-300">
              {request.command}
            </code>
          </div>

          {/* Status do Listener de Voz e Teclado */}
          <div className="flex items-center justify-between p-2 rounded bg-black/50 border border-jarvis-border/30 text-[11px] text-gray-400">
            <div className="flex items-center space-x-2">
              <Mic className={`w-3.5 h-3.5 ${isVoiceListening ? 'text-jarvis-cyan animate-pulse' : 'text-gray-500'}`} />
              <span className={isVoiceListening ? 'text-cyan-200' : 'text-gray-400'}>{voiceStatus}</span>
            </div>
            <div className="flex items-center space-x-1 text-[10px] text-gray-500">
              <Keyboard className="w-3.5 h-3.5" />
              <span>Atalhos Ativos</span>
            </div>
          </div>
        </div>

        {/* Botões de Ação com Badges de Teclado */}
        <div className="flex space-x-3">
          <button
            type="button"
            onClick={() => onDecision(request.ticket_id, false)}
            className="flex-1 flex items-center justify-center space-x-2 py-3 px-4 bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-500/50 rounded-lg font-hud font-bold tracking-wider transition-all duration-200 group"
          >
            <X className="w-4 h-4" />
            <span>CANCELAR</span>
            <kbd className="text-[10px] font-mono bg-red-950 border border-red-500/50 px-1.5 py-0.5 rounded text-red-200 ml-1.5 group-hover:border-red-400">
              Esc
            </kbd>
          </button>

          <button
            type="button"
            onClick={() => onDecision(request.ticket_id, true)}
            className="flex-1 flex items-center justify-center space-x-2 py-3 px-4 bg-emerald-950/50 hover:bg-emerald-800/70 text-emerald-300 border border-emerald-500/60 rounded-lg font-hud font-bold tracking-wider shadow-lg hover:shadow-emerald-500/30 transition-all duration-200 group"
          >
            <Check className="w-4 h-4" />
            <span>AUTORIZAR</span>
            <kbd className="text-[10px] font-mono bg-emerald-950 border border-emerald-500/50 px-1.5 py-0.5 rounded text-emerald-200 ml-1.5 group-hover:border-emerald-400">
              Enter
            </kbd>
          </button>
        </div>
      </div>
    </div>
  );
};
