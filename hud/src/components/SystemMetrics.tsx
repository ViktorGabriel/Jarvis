import React from 'react';
import { Cpu, HardDrive, Zap, Clock, ShieldCheck, Wifi } from 'lucide-react';
import { HardwareMetrics, DeepWorkStatus } from '../types';

interface SystemMetricsProps {
  hardware: HardwareMetrics;
  deepWork: DeepWorkStatus;
  isConnected: boolean;
  onToggleDeepWork: (enable: boolean) => void;
}

export const SystemMetrics: React.FC<SystemMetricsProps> = ({
  hardware,
  deepWork,
  isConnected,
  onToggleDeepWork,
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-jarvis-card backdrop-blur-md border border-jarvis-border rounded-lg p-4 font-mono text-xs text-gray-300 space-y-4">
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

      {/* CPU & RAM */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-black/50 p-2.5 rounded border border-jarvis-border/30">
          <div className="flex items-center justify-between text-gray-400 mb-1">
            <span className="flex items-center space-x-1">
              <Cpu className="w-3.5 h-3.5 text-jarvis-cyan" />
              <span>CPU</span>
            </span>
            <span className="text-white font-bold">{hardware.cpu_percent}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-jarvis-cyan h-full transition-all duration-500 shadow-hud-cyan"
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
            <span className="text-white font-bold">{hardware.ram_percent}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-jarvis-cyan h-full transition-all duration-500 shadow-hud-cyan"
              style={{ width: `${Math.min(hardware.ram_percent, 100)}%` }}
            />
          </div>
        </div>
      </div>

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
    </div>
  );
};
