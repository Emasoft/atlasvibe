/**
 * Virtual Environment types based on Python VenvManager module.
 */

export enum CheckStatus {
  PENDING = "pending",
  RUNNING = "running",
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
  SKIPPED = "skipped"
}

export interface CheckResult {
  name: string;
  status: CheckStatus;
  message: string;
  details?: Record<string, unknown>;
  duration?: number;
  timestamp?: string;
  recovery_action?: string;
}

export interface InstalledPackage {
  name: string;
  version: string;
}

export interface VenvStatus {
  exists: boolean;
  valid: boolean;
  python_version?: string;
  installed_packages: InstalledPackage[];
  last_regenerated?: string;
  health_checks: CheckResult[];
}

export interface VenvLog {
  block_name: string;
  start_time: string;
  duration?: number;
  success: boolean;
  error?: string;
  dependencies?: string[];
  python_version?: string;
  checks: CheckResult[];
  log_file?: string;
  backup_path?: string;
  rolled_back?: boolean;
  extracted_dependencies?: string[];
}

export interface RegenerateVenvResult {
  success: boolean;
  log_path: string;
  duration: number;
  error?: string;
  checks: CheckResult[];
}

export interface GetVenvLogsResponse {
  logs: VenvLog[];
}
