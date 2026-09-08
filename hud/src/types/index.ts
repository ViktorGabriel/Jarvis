export type AgentState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'awaiting_approval' | 'error';

export interface HardwareMetrics {
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
}

export interface DeepWorkStatus {
  is_active: boolean;
  project?: string;
  elapsed_seconds: number;
  remaining_seconds: number;
  target_seconds?: number;
}

export interface SystemMetricsEvent {
  hardware: HardwareMetrics;
  deep_work: DeepWorkStatus;
}

export interface SafetyApprovalRequest {
  ticket_id: string;
  action_type: string;
  description: string;
  command: string;
  risk_reason: string;
}

export interface DiffPreviewData {
  file_path: string;
  file_name: string;
  diff_text: string;
  additions: number;
  deletions: number;
  is_new_file: boolean;
}

export interface TranscriptMessage {
  id: string;
  sender: 'user' | 'jarvis' | 'system';
  text: string;
  timestamp: string;
}
