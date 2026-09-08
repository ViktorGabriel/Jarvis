import React from 'react';
import { FileCode, Check, X, GitCommit } from 'lucide-react';
import { DiffPreviewData } from '../types';

interface CodeDiffViewerProps {
  diff: DiffPreviewData | null;
  onApply: (filePath: string) => void;
  onDiscard: () => void;
}

export const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({ diff, onApply, onDiscard }) => {
  if (!diff) return null;

  const lines = diff.diff_text.split('\n');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-6">
      <div className="w-full max-w-4xl max-h-[85vh] bg-jarvis-bg/95 border border-jarvis-cyan/50 shadow-hud-cyan rounded-lg flex flex-col overflow-hidden">
        {/* Header do Diff */}
        <div className="flex items-center justify-between p-4 border-b border-jarvis-border bg-jarvis-card">
          <div className="flex items-center space-x-3">
            <FileCode className="w-6 h-6 text-jarvis-cyan" />
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-hud font-bold text-white tracking-wider">{diff.file_name}</span>
                {diff.is_new_file && (
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-1.5 py-0.5 rounded font-mono">
                    NOVO ARQUIVO
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 font-mono">{diff.file_path}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-1 rounded">
              +{diff.additions} linhas
            </span>
            <span className="text-red-400 bg-red-950/40 border border-red-500/30 px-2 py-1 rounded">
              -{diff.deletions} linhas
            </span>
          </div>
        </div>

        {/* Linhas de Diff */}
        <div className="flex-1 overflow-y-auto p-4 font-mono text-xs bg-black/70 space-y-0.5">
          {lines.map((line, idx) => {
            const isAdd = line.startsWith('+') && !line.startsWith('+++');
            const isDel = line.startsWith('-') && !line.startsWith('---');
            const isHeader = line.startsWith('@@');

            return (
              <div
                key={idx}
                className={`px-2 py-0.5 whitespace-pre font-mono rounded ${
                  isAdd
                    ? 'bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500'
                    : isDel
                    ? 'bg-red-950/40 text-red-300 border-l-2 border-red-500 line-through opacity-80'
                    : isHeader
                    ? 'text-cyan-400 bg-cyan-950/20 font-bold py-1 my-1'
                    : 'text-gray-300'
                }`}
              >
                {line || ' '}
              </div>
            );
          })}
        </div>

        {/* Rodapé de Ações */}
        <div className="p-4 border-t border-jarvis-border bg-jarvis-card flex justify-end space-x-3">
          <button
            onClick={onDiscard}
            className="flex items-center space-x-2 py-2 px-4 bg-gray-900/60 hover:bg-gray-800 text-gray-300 border border-gray-700 rounded font-hud font-bold tracking-wider transition-all"
          >
            <X className="w-4 h-4" />
            <span>DESCARTAR</span>
          </button>
          <button
            onClick={() => onApply(diff.file_path)}
            className="flex items-center space-x-2 py-2 px-5 bg-cyan-950/50 hover:bg-cyan-800/60 text-jarvis-cyan border border-jarvis-cyan rounded font-hud font-bold tracking-wider shadow-hud-cyan transition-all"
          >
            <Check className="w-4 h-4" />
            <span>APLICAR ALTERAÇÃO NO DISCO</span>
          </button>
        </div>
      </div>
    </div>
  );
};
