import React from 'react';
import { AgentOrb } from './AgentOrb';
import { AgentState } from '../types';

interface ArcReactorProps {
  state: AgentState;
  audioVolume: number;
}

export const ArcReactor: React.FC<ArcReactorProps> = ({ state, audioVolume }) => {
  return <AgentOrb state={state} audioVolume={audioVolume} />;
};
