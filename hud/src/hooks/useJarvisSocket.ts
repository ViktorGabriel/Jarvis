import { useState, useEffect, useRef, useCallback } from 'react';
import { AgentState, HardwareMetrics, DeepWorkStatus, SafetyApprovalRequest, DiffPreviewData, TranscriptMessage } from '../types';

export function useJarvisSocket(url: string = 'ws://127.0.0.1:8765') {
  const [isConnected, setIsConnected] = useState(false);
  const [agentState, setAgentState] = useState<AgentState>('idle');
  const [stateDetail, setStateDetail] = useState('');
  const [audioVolume, setAudioVolume] = useState(0);
  const [hardware, setHardware] = useState<HardwareMetrics>({
    cpu_percent: 0,
    ram_used_gb: 0,
    ram_total_gb: 0,
    ram_percent: 0,
  });
  const [deepWork, setDeepWork] = useState<DeepWorkStatus>({
    is_active: false,
    elapsed_seconds: 0,
    remaining_seconds: 0,
  });
  const [pendingApproval, setPendingApproval] = useState<SafetyApprovalRequest | null>(null);
  const [activeDiff, setActiveDiff] = useState<DiffPreviewData | null>(null);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const agentStateRef = useRef<AgentState>('idle');

  useEffect(() => {
    agentStateRef.current = agentState;
  }, [agentState]);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('[HUD] Conectado ao Python Core Daemon');
      };

      ws.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          const { event: eventType, data } = packet;

          switch (eventType) {
            case 'STATE_UPDATE':
              setAgentState(data.state || 'idle');
              if (data.detail) setStateDetail(data.detail);
              break;

            case 'AUDIO_METRICS': {
              const vol = data.volume || 0;
              setAudioVolume(vol);

              // 5. Suporte a Interrupção Imediata de Fala (Barge-in):
              // Se o assistente estiver falando e o volume do microfone ultrapassar o threshold (vol > 15.0),
              // muta o áudio local imediatamente e transiciona o estado para listening.
              if (agentStateRef.current === 'speaking' && vol > 15.0) {
                console.log('[Barge-in] Interrupção por voz do usuário detectada durante fala.');
                if (typeof window !== 'undefined' && window.speechSynthesis) {
                  window.speechSynthesis.cancel();
                }
                setAgentState('listening');
                setStateDetail('Interrompido por fala do usuário (Barge-in)...');
                if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                  socketRef.current.send(JSON.stringify({
                    event: 'USER_INPUT',
                    data: { text: '[INTERRUPCAO_BARGE_IN]' }
                  }));
                }
              }
              break;
            }

            case 'SYSTEM_METRICS':
              if (data.hardware) setHardware(data.hardware);
              if (data.deep_work) setDeepWork(data.deep_work);
              break;

            case 'SAFETY_APPROVAL_REQUEST':
              setPendingApproval(data);
              setAgentState('awaiting_approval');
              break;

            case 'DIFF_PREVIEW':
              setActiveDiff(data);
              break;

            case 'TRANSCRIPT': {
              const msgId = data.id || `msg_${Date.now()}_${Math.random().toString(36).substring(7)}`;
              const text = data.text || '';
              const sender = data.sender || 'jarvis';
              const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

              setMessages((prev) => {
                // Previne duplicação pelo ID
                if (data.id && prev.some((m) => m.id === data.id)) {
                  return prev;
                }
                // Previne duplicação pelo mesmo conteúdo consecutivo do mesmo remetente
                const last = prev[prev.length - 1];
                if (last && last.sender === sender && last.text === text) {
                  return prev;
                }
                return [
                  ...prev,
                  {
                    id: msgId,
                    sender,
                    text,
                    timestamp: time,
                  },
                ];
              });
              break;
            }

            default:
              break;
          }
        } catch (e) {
          console.error('[HUD] Erro ao decodificar mensagem WS:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        socketRef.current = null;
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (e) {
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  const sendEvent = useCallback((event: string, data: any = {}) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, data }));
    }
  }, []);

  const sendUserText = useCallback((text: string) => {
    if (!text.trim()) return;
    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        sender: 'user',
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
    sendEvent('USER_INPUT', { text });
  }, [sendEvent]);

  const resolveApproval = useCallback((ticketId: string, approved: boolean) => {
    sendEvent('SAFETY_DECISION', { ticket_id: ticketId, approved });
    setPendingApproval(null);
    setAgentState('idle');
  }, [sendEvent]);

  const toggleDeepWork = useCallback((enable: boolean, duration: number = 60) => {
    sendEvent('DEEP_WORK_TOGGLE', { enable, duration });
  }, [sendEvent]);

  return {
    isConnected,
    agentState,
    stateDetail,
    audioVolume,
    hardware,
    deepWork,
    pendingApproval,
    activeDiff,
    setActiveDiff,
    messages,
    sendUserText,
    resolveApproval,
    toggleDeepWork,
  };
}
