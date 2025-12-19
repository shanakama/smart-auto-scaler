// API Models matching Flask backend

export interface Pod {
  name: string;
  namespace: string;
  uid: string;
  labels: { [key: string]: string };
  owner?: {
    kind: string;
    name: string;
    uid: string;
  };
}

export interface PodMetrics {
  cpu_usage_cores: number;
  memory_usage_mb: number;
  timestamp: string;
}

export interface PodResources {
  cpu_requests_cores: number;
  memory_requests_mb: number;
  limits: {
    cpu_cores: number;
    memory_mb: number;
  };
}

export interface ScalingDecision {
  pod?: string;
  namespace: string;
  pod_name: string;
  action?: 'DECREASE' | 'MAINTAIN' | 'INCREASE';
  action_index?: number;
  confidence?: number | {
    cpu: number;
    memory: number;
  };
  q_values?: number[];
  current_resources?: {
    cpu_cores: number;
    memory_mb: number;
  };
  proposed_resources?: {
    cpu_cores: number;
    memory_mb: number;
  };
  current_usage?: {
    cpu_cores: number;
    memory_mb: number;
  };
  timestamp: string;
  applied?: boolean;
  reason?: string;
  // New enhanced format fields
  can_scale?: boolean;
  cpu_action?: 'DECREASE' | 'MAINTAIN' | 'INCREASE';
  memory_action?: 'DECREASE' | 'MAINTAIN' | 'INCREASE';
  current_metrics?: {
    cpu_limit: number;
    cpu_usage: number;
    memory_limit_mb: number;
    memory_usage_mb: number;
  };
  future_predictions?: {
    cpu: number;
    memory: number;
  };
  resource_changes?: {
    cpu: {
      action: string;
      change_percent: number;
      current: number;
      new: number;
    };
    memory: {
      action: string;
      change_percent: number;
      current: number;
      new: number;
    };
  };
  utilization?: {
    cpu_percentage: number;
    memory_percentage: number;
  };
}

export interface Statistics {
  action_distribution: {
    cpu_actions: {
      DECREASE: number;
      INCREASE: number;
      MAINTAIN: number;
    };
    memory_actions: {
      DECREASE: number;
      INCREASE: number;
      MAINTAIN: number;
    };
  };
  model_performance: {
    average_cpu_confidence: number;
    average_memory_confidence: number;
    model_type: string;
  };
  overview: {
    applied_scalings: number;
    scaling_rate: number;
    total_decisions: number;
    total_pods_monitored: number;
  };
  resource_utilization: {
    average_cpu_usage: number;
    average_memory_usage_mb: number;
  };
  system_status: {
    cooldown_period_minutes: number;
    dry_run_mode: boolean;
    kubernetes_available: boolean;
    scale_factor: number;
  };
  timestamp: string;
}

export interface Config {
  model_path: string;
  state_dim: number;
  action_dim: number;
  history_window: number;
  min_cpu: number;
  max_cpu: number;
  min_memory: number;
  max_memory: number;
  scale_factor: number;
  dry_run: boolean;
  in_cluster: boolean;
  namespaces: string[];
  auto_scale_enabled: boolean;
  auto_scale_interval: number;
  scaling_cooldown: number;
}

export interface AutoscaleStatus {
  enabled: boolean;
  running: boolean;
  interval_seconds: number;
  thread_alive: boolean;
}

export interface HealthStatus {
  status: string;
  service: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
