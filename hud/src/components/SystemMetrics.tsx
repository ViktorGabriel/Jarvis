import React, { useState } from 'react';
import {
  Cpu,
  HardDrive,
  Zap,
  Clock,
  ShieldCheck,
  Wifi,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Activity,
  Database,
} from 'lucide-react';
import { HardwareMetrics, DeepWorkStatus } from '../types';

interface SystemMetricsProps {
  hardware: HardwareMetrics;
  deepWork: DeepWorkStatus;
  isConnected: boolean;
  onToggleDeepWork: (enable: boolean) => void;
  onActivateWorkspace?: (mode: string) => void;
}

export const SystemMetrics: React.FC<SystemMetricsProps> = ({
  hardware,
  deepWork,
  isConnected,
  onToggleDeepWork,
  onActivateWorkspace,
}) => {
  const [showProcesses, setShowProcesses] = useState(false);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getMetricStyle = (percent: number) => {
    if (percent >= 88) {
      return {
        textColor: 'text-red-400 font-bold animate-pulse',
        barColor: 'bg-red-500',
        glow: 'shadow-[0_0_10px_rgba(239,68,68,0.6)]',
      };
    }
    if (percent >= 70) {
      return {
        textColor: 'text-jarvis-amber font-bold',
        barColor: 'bg-amber-400',
        glow: 'shadow-[0_0_10px_rgba(251,191,36,0.5)]',
      };
    }
    return {
      textColor: 'text-white font-bold',
      barColor: 'bg-jarvis-cyan',
      glow: 'shadow-hud-cyan',
    };
  };

  const cpuStyle = getMetricStyle(hardware.cpu_percent);
  const ramStyle = getMetricStyle(hardware.ram_percent);
  const diskStyle = getMetricStyle(hardware.disk_percent || 0);

  return (
    <div className="bg-jarvis-card backdrop-blur-md border border-jarvis-border rounded-lg p-4 font-mono text-xs text-gray-300 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-jarvis-border/40 pb-2">
        <span className="font-hud text-sm font-bold text-jarvis-cyan uppercase tracking-wider flex items-center space-x-2">
          <Zap className="w-4 h-4" />
          <span>TELEMETRIA DE SISTEMA</span>
        </span>
        <div className="flex items-center space-x-1.5">
          <Wifi className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-red-500'}`} />
          <span className={isConnected ? 'text-emerald-400' : 'text-red-500 font-bold'}>
            {isConnected ? 'DAEMON ONLINE' : 'DESCONECTADO'}
          </span>
        </div>
      </div>

      {/* Proactive Alert Banner */}
      {hardware.alert && (
        <div
          className={`p-2.5 rounded border flex items-center space-x-2.5 text-xs animate-pulse ${
            hardware.alert.level === 'critical'
              ? 'bg-red-950/70 border-red-500 text-red-200'
              : 'bg-amber-950/70 border-amber-500 text-amber-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-300" />
          <div className="flex-1 leading-tight">
            <span className="font-bold uppercase text-[10px] tracking-wider block">
              {hardware.alert.level === 'critical' ? 'SOBRECARGA CRÍTICA DETECTADA' : 'AVISO DE RECURSO'}
            </span>
            <span className="text-[11px]">{hardware.alert.message}</span>
          </div>
        </div>
      )}

      {/* CPU & RAM Gauges */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-black/50 p-2.5 rounded border border-jarvis-border/30">
          <div className="flex items-center justify-between text-gray-400 mb-1">
            <span className="flex items-center space-x-1">
              <Cpu className="w-3.5 h-3.5 text-jarvis-cyan" />
              <span>CPU</span>
              {hardware.cpu_count && (
                <span className="text-[10px] text-gray-500">({hardware.cpu_count}c)</span>
              )}
            </span>
            <span className={cpuStyle.textColor}>{hardware.cpu_percent}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`${cpuStyle.barColor} ${cpuStyle.glow} h-full transition-all duration-500`}
              style={{ width: `${Math.min(hardware.cpu_percent, 100)}%` }}
            />
          </div>
        </div>

        <div className="bg-black/50 p-2.5 rounded border border-jarvis-border/30">
          <div className="flex items-center justify-between text-gray-400 mb-1">
            <span className="flex items-center space-x-1">
              <HardDrive className="w-3.5 h-3.5 text-jarvis-cyan" />
              <span>RAM</span>
            </span>
            <span className={ramStyle.textColor}>{hardware.ram_percent}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`${ramStyle.barColor} ${ramStyle.glow} h-full transition-all duration-500`}
              style={{ width: `${Math.min(hardware.ram_percent, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>{hardware.ram_used_gb} GB</span>
            <span>{hardware.ram_total_gb} GB</span>
          </div>
        </div>
      </div>

      {/* Armazenamento / Disco */}
      {hardware.disk_total_gb !== undefined && (
        <div className="bg-black/50 p-2.5 rounded border border-jarvis-border/30">
          <div className="flex items-center justify-between text-gray-400 mb-1">
            <span className="flex items-center space-x-1">
              <Database className="w-3.5 h-3.5 text-jarvis-cyan" />
              <span>DISCO DO SISTEMA</span>
            </span>
            <span className={diskStyle.textColor}>{hardware.disk_percent}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`${diskStyle.barColor} ${diskStyle.glow} h-full transition-all duration-500`}
              style={{ width: `${Math.min(hardware.disk_percent || 0, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>{hardware.disk_used_gb} GB em uso</span>
            <span>{hardware.disk_free_gb} GB livres</span>
          </div>
        </div>
      )}

      {/* Top Processos (Colapsável) */}
      {hardware.top_processes && hardware.top_processes.length > 0 && (
        <div className="bg-black/50 rounded border border-jarvis-border/30 overflow-hidden">
          <button
            onClick={() => setShowProcesses(!showProcesses)}
            className="w-full flex items-center justify-between p-2 hover:bg-white/5 transition-colors text-gray-400 hover:text-white"
          >
            <span className="flex items-center space-x-1.5 font-hud text-[11px] font-bold text-gray-300">
              <Activity className="w-3.5 h-3.5 text-jarvis-cyan" />
              <span>TOP PROCESSOS EM MEMÓRIA</span>
            </span>
            {showProcesses ? (
              <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            )}
          </button>

          {showProcesses && (
            <div className="p-2 pt-0 space-y-1.5 border-t border-jarvis-border/20">
              {hardware.top_processes.slice(0, 5).map((proc) => (
                <div
                  key={proc.pid}
                  className="flex items-center justify-between text-[11px] py-1 px-2 rounded bg-black/40 border border-jarvis-border/20"
                >
                  <div className="truncate max-w-[150px] text-gray-200" title={proc.name}>
                    <span className="text-gray-500 mr-1.5">[{proc.pid}]</span>
                    <span className="font-semibold">{proc.name}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-right">
                    <span className="text-jarvis-cyan font-bold">{proc.memory_mb} MB</span>
                    {proc.cpu_percent > 0 && (
                      <span className="text-gray-400 text-[10px]">({proc.cpu_percent}%)</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Bloco de Deep Work */}
      <div className="bg-black/60 p-3 rounded border border-jarvis-border/40">
        <div className="flex items-center justify-between mb-2">
          <span className="font-hud font-bold text-white flex items-center space-x-1.5">
            <Clock className="w-4 h-4 text-jarvis-amber" />
            <span>MODO DEEP WORK</span>
          </span>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              deepWork.is_active
                ? 'bg-amber-500/20 text-jarvis-amber border border-jarvis-amber/40 animate-pulse'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            {deepWork.is_active ? 'ATIVO' : 'INATIVO'}
          </span>
        </div>

        {deepWork.is_active ? (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-gray-400">
              <span>Decorrido: {formatTime(deepWork.elapsed_seconds)}</span>
              <span>Restante: {formatTime(deepWork.remaining_seconds)}</span>
            </div>
            <button
              onClick={() => onToggleDeepWork(false)}
              className="w-full py-1.5 bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-500/40 rounded font-hud font-bold tracking-wider transition-all"
            >
              ENCERRAR FOCO
            </button>
          </div>
        ) : (
          <button
            onClick={() => onToggleDeepWork(true)}
            className="w-full py-1.5 bg-cyan-950/30 hover:bg-cyan-900/50 text-jarvis-cyan border border-jarvis-cyan/40 rounded font-hud font-bold tracking-wider shadow-sm transition-all"
          >
            INICIAR SESSÃO DE 60 MIN
          </button>
        )}
      </div>

      {/* Workspaces / Modos de Foco */}
      <div className="bg-black/60 p-3 rounded border border-jarvis-border/40 space-y-2">
        <span className="font-hud font-bold text-white flex items-center space-x-1.5 text-xs">
          <Zap className="w-4 h-4 text-jarvis-cyan" />
          <span>WORKSPACES TÁTICOS</span>
        </span>
        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            onClick={() => onActivateWorkspace?.('dev')}
            className="p-2 bg-cyan-950/30 hover:bg-cyan-900/60 border border-jarvis-cyan/30 rounded flex flex-col items-center justify-center space-y-1 transition-all"
            title="VS Code, Navegador e Spotify"
          >
            <Cpu className="w-4 h-4 text-jarvis-cyan" />
            <span className="text-[10px] font-bold text-cyan-200">MODO DEV</span>
          </button>
          <button
            onClick={() => onActivateWorkspace?.('study')}
            className="p-2 bg-amber-950/30 hover:bg-amber-900/60 border border-jarvis-amber/30 rounded flex flex-col items-center justify-center space-y-1 transition-all"
            title="Obsidian, Documentação e Referências"
          >
            <HardDrive className="w-4 h-4 text-jarvis-amber" />
            <span className="text-[10px] font-bold text-amber-200">ESTUDO</span>
          </button>
          <button
            onClick={() => onActivateWorkspace?.('deep_work')}
            className="p-2 bg-red-950/30 hover:bg-red-900/60 border border-red-500/30 rounded flex flex-col items-center justify-center space-y-1 transition-all"
            title="Foco Total sem Distrações"
          >
            <ShieldCheck className="w-4 h-4 text-red-400" />
            <span className="text-[10px] font-bold text-red-200">DEEP WORK</span>
          </button>
          <button
            onClick={() => onActivateWorkspace?.('rest')}
            className="p-2 bg-blue-950/30 hover:bg-blue-900/60 border border-blue-500/30 rounded flex flex-col items-center justify-center space-y-1 transition-all"
            title="Encerrar Ferramentas e Descansar"
          >
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-[10px] font-bold text-blue-200">DESCANSO</span>
          </button>
        </div>
      </div>
    </div>
  );
};
