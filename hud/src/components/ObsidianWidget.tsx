import React, { useState } from 'react';
import { BookOpen, Send, Calendar, CheckSquare, Plus } from 'lucide-react';

interface ObsidianWidgetProps {
  onQuickCapture: (thought: string) => void;
  onRequestDailyNote: () => void;
}

export const ObsidianWidget: React.FC<ObsidianWidgetProps> = ({
  onQuickCapture,
  onRequestDailyNote,
}) => {
  const [thought, setThought] = useState('');
  const today = new Date().toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!thought.trim()) return;
    onQuickCapture(`Criar nota de pensamento rápido: ${thought}`);
    setThought('');
  };

  return (
    <div className="bg-jarvis-card backdrop-blur-md border border-jarvis-border rounded-lg p-4 font-mono text-xs text-gray-300 space-y-4">
      <div className="flex items-center justify-between border-b border-jarvis-border/40 pb-2">
        <span className="font-hud text-sm font-bold text-jarvis-cyan uppercase tracking-wider flex items-center space-x-2">
          <BookOpen className="w-4 h-4" />
          <span>SEGUNDO CÉREBRO (OBSIDIAN)</span>
        </span>
        <div className="flex items-center space-x-1.5 text-gray-400">
          <Calendar className="w-3.5 h-3.5 text-jarvis-amber" />
          <span>{today}</span>
        </div>
      </div>

      {/* Ação rápida da Daily Note */}
      <div className="flex items-center justify-between bg-black/40 p-2.5 rounded border border-jarvis-border/20">
        <div>
          <span className="text-white font-bold block">Daily Note de Hoje</span>
          <span className="text-[10px] text-gray-400">Time-blocking & Retrospectiva</span>
        </div>
        <button
          onClick={onRequestDailyNote}
          className="py-1 px-3 bg-cyan-950/40 hover:bg-cyan-900/60 text-jarvis-cyan border border-jarvis-cyan/30 rounded font-hud font-bold text-xs transition-all"
        >
          SINCRONIZAR
        </button>
      </div>

      {/* Caixa de Captura Rápida para o Human/Inbox */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <label className="text-[11px] text-gray-400 flex items-center space-x-1">
          <Plus className="w-3 h-3 text-jarvis-cyan" />
          <span>Captura Rápida (Human/Inbox):</span>
        </label>
        <div className="flex space-x-2">
          <input
            type="text"
            value={thought}
            onChange={(e) => setThought(e.target.value)}
            placeholder="Dite ou digite uma ideia rápida..."
            className="flex-1 bg-black/70 border border-jarvis-border/40 rounded px-2.5 py-1.5 text-white placeholder-gray-500 focus:outline-none focus:border-jarvis-cyan text-xs"
          />
          <button
            type="submit"
            className="p-1.5 bg-cyan-950/60 hover:bg-cyan-800 text-jarvis-cyan border border-jarvis-cyan/40 rounded transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
