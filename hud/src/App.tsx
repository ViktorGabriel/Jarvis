import React, { useState, useEffect, useRef } from 'react';
import { useJarvisSocket } from './hooks/useJarvisSocket';
import { AgentOrb } from './components/AgentOrb';
import { ToolExecutionPill } from './components/ToolExecutionPill';
import { ApprovalModal } from './components/ApprovalModal';
import { CodeDiffViewer } from './components/CodeDiffViewer';
import { SystemMetrics } from './components/SystemMetrics';
import { ObsidianWidget } from './components/ObsidianWidget';
import {
  Mic,
  MicOff,
  Send,
  Pin,
  Minus,
  X,
  Shield,
  Activity,
  Code2,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';

export const App: React.FC = () => {
  const {
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
  } = useJarvisSocket();

  const [inputVal, setInputVal] = useState('');
  const [isPinned, setIsPinned] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 0. Reconhecimento de Voz Contínuo via Web Speech API
  const {
    isListening: isVoiceListening,
    interimTranscript,
    isSupported: isVoiceSupported,
    startListening: startVoiceListening,
    toggleListening: toggleVoiceListening,
  } = useSpeechRecognition({
    onFinalResult: (transcript) => {
      sendUserText(transcript);
    },
  });

  // Inicia o microfone automaticamente se houver suporte
  useEffect(() => {
    if (isVoiceSupported) {
      startVoiceListening();
    }
  }, [isVoiceSupported, startVoiceListening]);

  // 1. Foco automático ao acionar atalho global (window-shown)
  useEffect(() => {
    const unsub = (window as any).jarvisElectron?.onWindowShown?.(() => {
      inputRef.current?.focus();
    });
    return () => {
      unsub?.();
    };
  }, []);

  // 2. Atalho Esc fora de modais críticos para ocultar instantaneamente o HUD
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Se estiver com modal de governança aberto, o próprio modal cuida da rejeição
        if (pendingApproval) return;
        // Se estiver com diff aberto, fecha o diff
        if (activeDiff) {
          setActiveDiff(null);
          return;
        }
        // Se tela limpa, oculta o HUD sem encerrar o daemon de fundo
        if ((window as any).jarvisElectron?.hide) {
          (window as any).jarvisElectron.hide();
        } else if ((window as any).jarvisElectron?.close) {
          (window as any).jarvisElectron.close();
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [pendingApproval, activeDiff, setActiveDiff]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    sendUserText(inputVal);
    setInputVal('');
  };

  const handleTogglePin = () => {
    const next = !isPinned;
    setIsPinned(next);
    (window as any).jarvisElectron?.togglePin(next);
  };

  const handleToggleFullscreen = () => {
    const next = !isFullscreen;
    setIsFullscreen(next);
    if ((window as any).jarvisElectron?.toggleFullscreen) {
      (window as any).jarvisElectron.toggleFullscreen();
    } else {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    }
  };

  const handleMinimize = () => {
    (window as any).jarvisElectron?.minimize();
  };

  const handleClose = () => {
    (window as any).jarvisElectron?.close();
  };

  const getStateLabel = () => {
    switch (agentState) {
      case 'listening':
        return { text: 'OUVINDO...', color: 'text-jarvis-cyan animate-pulse' };
      case 'thinking':
        return { text: 'PROCESSANDO...', color: 'text-jarvis-amber animate-pulse' };
      case 'speaking':
        return { text: 'TRANSMITINDO ÁUDIO', color: 'text-jarvis-cyan text-glow' };
      case 'awaiting_approval':
        return { text: 'TRAVAMENTO PREVENTIVO', color: 'text-jarvis-alert text-glow-alert animate-bounce' };
      case 'error':
        return { text: 'ERRO OPERACIONAL', color: 'text-red-500' };
      default:
        if (isVoiceListening) {
          return { text: 'ONLINE • MICROFONE ATIVO', color: 'text-jarvis-cyan' };
        }
        return { text: 'ONLINE • AGUARDANDO', color: 'text-gray-400' };
    }
  };

  const stateInfo = getStateLabel();

  return (
    <div className="w-screen h-screen bg-jarvis-bg/90 text-white font-mono flex flex-col select-none overflow-hidden border border-jarvis-border shadow-hud-cyan rounded-xl backdrop-blur-xl scanlines">
      {/* Barra de Título Frameless Draggable */}
      <header
        className="h-10 bg-black/60 border-b border-jarvis-border/40 flex items-center justify-between px-4"
        style={{ WebkitAppRegion: 'drag' } as any}
      >
        <div className="flex items-center space-x-3">
          <div className="w-2.5 h-2.5 rounded-full bg-jarvis-cyan shadow-hud-cyan animate-ping" />
          <span className="font-hud font-bold text-sm tracking-widest text-jarvis-cyan uppercase">
            J.A.R.V.I.S. • SISTEMA TÁTICO
          </span>
          <span className="text-[10px] text-gray-500 bg-gray-900/60 px-2 py-0.5 rounded border border-gray-800">
            GEMINI FLASH CORE
          </span>
        </div>

        {/* Indicador de Atividade / Tool Execution Pill */}
        <div style={{ WebkitAppRegion: 'no-drag' } as any}>
          <ToolExecutionPill state={agentState} detail={stateDetail} />
        </div>

        {/* Controles de Janela */}
        <div
          className="flex items-center space-x-1"
          style={{ WebkitAppRegion: 'no-drag' } as any}
        >
          <button
            onClick={handleTogglePin}
            className={`p-1 rounded hover:bg-white/10 transition-all ${
              isPinned ? 'text-jarvis-cyan' : 'text-gray-400 hover:text-white'
            }`}
            title="Fixar no Topo"
          >
            <Pin className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleToggleFullscreen}
            className={`p-1 rounded hover:bg-white/10 transition-all ${
              isFullscreen ? 'text-jarvis-cyan' : 'text-gray-400 hover:text-white'
            }`}
            title={isFullscreen ? "Sair da Tela Cheia" : "Tela Cheia"}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleMinimize}
            className="p-1 rounded text-gray-400 hover:bg-white/10 hover:text-white transition-all"
            title="Minimizar"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleClose}
            className="p-1 rounded text-gray-400 hover:bg-red-500/20 hover:text-red-400 transition-all"
            title="Fechar / Ocultar"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Conteúdo Principal em Grid */}
      <main className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-hidden">
        {/* Coluna Esquerda: Telemetria e Obsidian */}
        <section className="col-span-3 flex flex-col space-y-4 overflow-y-auto">
          <SystemMetrics
            hardware={hardware}
            deepWork={deepWork}
            isConnected={isConnected}
            onToggleDeepWork={(enable) => toggleDeepWork(enable, 60)}
            onActivateWorkspace={(mode) => sendUserText(`ativar workspace ${mode}`)}
          />

          <ObsidianWidget
            onQuickCapture={sendUserText}
            onRequestDailyNote={() => sendUserText('J.A.R.V.I.S, gere minha Daily Note de hoje')}
          />
        </section>

        {/* Coluna Central: O Reator Arc e Status Holográfico */}
        <section className="col-span-5 flex flex-col items-center justify-between p-2">
          {/* Badge de Estado Superior */}
          <div className="flex flex-col items-center">
            <div className="flex items-center space-x-2 bg-black/60 border border-jarvis-border/40 px-4 py-1.5 rounded-full backdrop-blur-md">
              <Activity className="w-4 h-4 text-jarvis-cyan" />
              <span className={`font-hud font-bold text-xs tracking-widest ${stateInfo.color}`}>
                {stateInfo.text}
              </span>
            </div>
            {stateDetail && (
              <span className="text-[11px] text-gray-400 mt-1 max-w-xs text-center truncate">
                {stateDetail}
              </span>
            )}
          </div>

          {/* O Reator Central 3D / Agent Orb */}
          <div className="my-auto py-2">
            <AgentOrb state={agentState} audioVolume={audioVolume} />
          </div>

          {/* Atalho Global e Dica de Voz */}
          <div className="text-center font-mono text-[11px] text-gray-400 border border-jarvis-border/20 bg-black/40 px-4 py-1.5 rounded-full">
            Pressione <kbd className="text-jarvis-cyan font-bold">Ctrl+Shift+J</kbd> para alternar overlay • <kbd className="text-gray-300 font-bold">Esc</kbd> para ocultar
          </div>
        </section>

        {/* Coluna Direita: Feed de Comunicação e Input */}
        <section className="col-span-4 flex flex-col bg-jarvis-card backdrop-blur-md border border-jarvis-border rounded-lg overflow-hidden">
          <div className="p-3 border-b border-jarvis-border/40 flex items-center justify-between bg-black/40">
            <span className="font-hud font-bold text-xs text-jarvis-cyan uppercase tracking-wider flex items-center space-x-1.5">
              <Shield className="w-3.5 h-3.5" />
              <span>REGISTRO DE INTERAÇÃO</span>
            </span>
            <span className="text-[10px] text-gray-400">
              {messages.length} eventos
            </span>
          </div>

          {/* Lista de Mensagens */}
          <div className="flex-1 p-3 overflow-y-auto space-y-3 text-xs">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center text-gray-500 text-xs px-4">
                J.A.R.V.I.S. conectado e pronto. Dite um comando ou digite na barra abaixo.
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`p-2.5 rounded border ${
                    m.sender === 'user'
                      ? 'bg-cyan-950/20 border-jarvis-cyan/30 text-cyan-200 ml-4'
                      : 'bg-black/60 border-jarvis-border/40 text-gray-200 mr-4'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
                    <span className="font-bold text-jarvis-cyan uppercase">
                      {m.sender === 'user' ? 'VIKTOR' : 'J.A.R.V.I.S.'}
                    </span>
                    <span>{m.timestamp}</span>
                  </div>
                  <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>
                </div>
              ))
            )}
          </div>

          {/* Transcrição de Fala em Tempo Real (Interim Preview) */}
          {interimTranscript && (
            <div className="px-3 py-1.5 bg-cyan-950/40 border-t border-cyan-800/40 text-[11px] text-cyan-300 flex items-center space-x-2 animate-pulse">
              <Mic className="w-3.5 h-3.5 text-jarvis-cyan flex-shrink-0" />
              <span className="truncate">Ouvindo: &ldquo;{interimTranscript}&rdquo;</span>
            </div>
          )}

          {/* Barra de Entrada de Texto com Auto-Foco e Controle Vocal */}
          <form
            onSubmit={handleSend}
            className="p-2 bg-black/60 border-t border-jarvis-border/40 flex items-center space-x-2"
          >
            {isVoiceSupported && (
              <button
                type="button"
                onClick={toggleVoiceListening}
                className={`p-2 rounded border transition-all ${
                  isVoiceListening
                    ? 'bg-red-950/60 border-red-500/60 text-red-400 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.3)]'
                    : 'bg-black/80 hover:bg-gray-800 text-gray-400 hover:text-white border-jarvis-border/40'
                }`}
                title={isVoiceListening ? "Microfone ativo (clique para pausar)" : "Ativar microfone"}
              >
                {isVoiceListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
              </button>
            )}
            <input
              ref={inputRef}
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder={isVoiceListening ? "Fale um comando ou digite aqui..." : "Digite uma instrução ou pergunta..."}
              className="flex-1 bg-black/80 border border-jarvis-border/40 rounded px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-jarvis-cyan"
            />
            <button
              type="submit"
              className="p-2 bg-cyan-950/60 hover:bg-cyan-800 text-jarvis-cyan border border-jarvis-cyan/40 rounded transition-all"
              title="Enviar comando"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </section>
      </main>

      {/* Modais Críticos Globais */}
      <ApprovalModal
        request={pendingApproval}
        onDecision={resolveApproval}
      />

      <CodeDiffViewer
        diff={activeDiff}
        onApply={(filePath) => {
          sendUserText(`J.A.R.V.I.S, aplique as alterações no arquivo ${filePath}`);
          setActiveDiff(null);
        }}
        onDiscard={() => setActiveDiff(null)}
      />
    </div>
  );
};
