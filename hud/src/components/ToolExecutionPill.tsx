import React from 'react';
import {
  Loader2,
  Terminal,
  GitBranch,
  FileEdit,
  Server,
  FlaskConical,
  Wrench,
} from 'lucide-react';
import { AgentState } from '../types';

interface ToolExecutionPillProps {
  state: AgentState;
  detail?: string;
}

export const ToolExecutionPill: React.FC<ToolExecutionPillProps> = ({ state, detail }) => {
  const isThinking = state === 'thinking';
  const hasDetail = Boolean(detail && detail.trim().length > 0);

  // Exibe a pílula sempre que estiver pensando ou houver detalhe ativo de ferramenta
  const isVisible = isThinking || (state !== 'error' && state !== 'idle' && hasDetail);

  if (!isVisible && !hasDetail) {
    return null;
  }

  const cleanDetail = (detail || '').trim();

  // Identifica o ícone e categoria tática baseado no texto
  const getToolMeta = () => {
    const lower = cleanDetail.toLowerCase();
    if (lower.includes('docker') || lower.includes('container') || lower.includes('compose')) {
      return {
        icon: <Server className="w-3.5 h-3.5 text-blue-400 animate-pulse" />,
        prefix: 'INFRA',
        color: 'border-blue-500/40 shadow-[0_0_12px_rgba(59,130,246,0.35)]',
      };
    }
    if (lower.includes('git') || lower.includes('commit') || lower.includes('push') || lower.includes('diff')) {
      return {
        icon: <GitBranch className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />,
        prefix: 'GIT',
        color: 'border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.35)]',
      };
    }
    if (lower.includes('test') || lower.includes('pytest') || lower.includes('suíte')) {
      return {
        icon: <FlaskConical className="w-3.5 h-3.5 text-purple-400 animate-pulse" />,
        prefix: 'TESTS',
        color: 'border-purple-500/40 shadow-[0_0_12px_rgba(168,85,247,0.35)]',
      };
    }
    if (lower.includes('inbox') || lower.includes('journal') || lower.includes('obsidian') || lower.includes('nota')) {
      return {
        icon: <FileEdit className="w-3.5 h-3.5 text-jarvis-amber animate-pulse" />,
        prefix: 'VAULT',
        color: 'border-jarvis-amber/40 shadow-[0_0_12px_rgba(255,183,3,0.35)]',
      };
    }
    if (lower.includes('sop') || lower.includes('procedimento') || lower.includes('workflow')) {
      return {
        icon: <Wrench className="w-3.5 h-3.5 text-jarvis-cyan animate-pulse" />,
        prefix: 'SOP',
        color: 'border-jarvis-cyan/40 shadow-hud-cyan',
      };
    }
    return {
      icon: <Terminal className="w-3.5 h-3.5 text-jarvis-cyan animate-pulse" />,
      prefix: 'EXEC',
      color: 'border-jarvis-cyan/40 shadow-hud-cyan',
    };
  };

  const meta = getToolMeta();
  const label = cleanDetail || 'Processando rotina em background...';

  return (
    <div
      className={`transition-all duration-300 transform ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2 pointer-events-none'
      }`}
    >
      <div
        className={`flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-black/80 backdrop-blur-xl border ${meta.color} text-xs font-mono`}
      >
        <Loader2 className="w-3.5 h-3.5 text-jarvis-cyan animate-spin flex-shrink-0" />
        <div className="flex items-center space-x-1.5 flex-shrink-0">
          {meta.icon}
          <span className="text-[10px] font-hud font-bold tracking-wider text-gray-400 uppercase">
            [{meta.prefix}]
          </span>
        </div>
        <span className="text-gray-200 text-[11px] truncate max-w-xs sm:max-w-sm">
          {label}
        </span>
      </div>
    </div>
  );
};
