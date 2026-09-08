export type AgentState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'awaiting_approval' | 'error';

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_mb: number;
  memory_percent?: number;
}

export interface TelemetryAlert {
  type: string;
  level: 'warning' | 'critical';
  message: string;
  percent?: number;
  free_gb?: number;
  should_notify?: boolean;
}

export interface HardwareMetrics {
  cpu_percent: number;
  cpu_count?: number;
  cpu_physical_count?: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_free_gb?: number;
  ram_percent: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  disk_free_gb?: number;
  disk_percent?: number;
  top_processes?: ProcessInfo[];
  alert?: TelemetryAlert | null;
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
