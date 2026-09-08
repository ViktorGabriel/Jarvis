export type WorkspaceModeKey = 'dev' | 'study' | 'deep_work' | 'rest';

export interface WorkspaceProfile {
  id: WorkspaceModeKey;
  name: string;
  description: string;
  apps: string[];
  speechReply: string;
  urls?: string[];
  deepWork?: boolean;
}

export const WORKSPACE_PROFILES: Record<WorkspaceModeKey, WorkspaceProfile> = {
  dev: {
    id: 'dev',
    name: 'Desenvolvimento',
    description: 'Abre VS Code, navegador em localhost e playlist de foco no Spotify.',
    apps: ['VS Code', 'Navegador', 'Spotify'],
    urls: ['http://localhost:5173', 'https://github.com'],
    speechReply: 'Protocolo de desenvolvimento ativado. Ambiente de engenharia pronto, senhor.',
  },
  study: {
    id: 'study',
    name: 'Estudo e Pesquisa',
    description: 'Abre cofre do Obsidian, documentações e volume equilibrado.',
    apps: ['Obsidian', 'Navegador'],
    urls: ['https://google.com'],
    speechReply: 'Modo de estudo iniciado. Cofre do Obsidian pronto, senhor.',
  },
  deep_work: {
    id: 'deep_work',
    name: 'Deep Work',
    description: 'Editor de código, Obsidian e cronômetro de 60min sem distrações.',
    apps: ['VS Code', 'Obsidian'],
    deepWork: true,
    speechReply: 'Modo Deep Work iniciado. Foco tático ativado por 60 minutos.',
  },
  rest: {
    id: 'rest',
    name: 'Descanso',
    description: 'Encerramento de tarefas de trabalho e pausa no foco.',
    apps: ['Spotify'],
    speechReply: 'Ambiente de trabalho recolhido. Tenha um bom descanso, senhor.',
  },
};
