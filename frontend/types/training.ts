/**
 * Training types for Fine-tuning Training API
 */

/**
 * Backend training status values
 */
export type TrainingStatus = 'Prepare' | 'Training' | 'Completed' | 'Failed';

/**
 * Optimizer types supported
 */
export type OptimizerType = 'AdamW' | 'AdamW8bit';

/**
 * Model dtype options for training
 */
export type TrainingDtype = 'bfloat16' | 'float8_e4m3fn';

/**
 * TrainingState from backend (matches backend/training/state.py)
 */
export interface TrainingState {
  // Job Metadata
  task_id: string;
  job_name: string;
  project_id: string;
  config: TrainConfig;
  created_at: string;

  // Progress
  current_step: number | null;
  estimated_total_steps: number | null;
  current_epoch: number | null;
  total_epochs: number | null;

  // Training Parameters
  learning_rate: number | null;
  batch_size: number | null;
  accumlate_grad_steps: number | null;

  // Loss Metrics
  current_loss: number | null;
  current_diffusion_loss: number | null;
  current_ce_loss: number | null;
  average_epoch_loss: number | null;
  average_epoch_diffusion_loss: number | null;
  average_epoch_ce_loss: number | null;

  // Timing
  start_time: string | null;
  current_timestamp: string | null;
  estimated_total_elpase: number | null;
  latest_epoch_elapsed: number | null;
  latest_step_elapsed: number | null;
  average_step_time: number | null;
  steps_per_second: number | null;

  // Status
  status: TrainingStatus;

  // TensorBoard
  tensorboard_logdir: string | null;

  // Output Files
  lora_files: string[];
  final_lora_file: string | null;
  all_lora_files?: string[];  // Combined list of all LoRA files (added by backend)

  // Error message (if failed)
  error_message?: string | null;
}

/**
 * Training configuration matching TrainConfig from trainer.py
 */
export interface TrainConfig {
  lora_name: string;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  dataset_path: string | null;
  output_dir: string;
  multiplier: number;
  lora_dim: number;
  lora_alpha: number | null;
  lora_dropout: number | null;
  model_path: string | null;
  number_of_layers: number;
  dtype: TrainingDtype;
  model_config_path: string | null;
  optimizer_type: OptimizerType;
  optimizer_args: string[] | null;
  seeds: number;
  dataset_repeats: number;
  speech_compress_ratio: number;
  semantic_dim: number;
  diffusion_loss_weight: number;
  ce_loss_weight: number;
  device: string;
  gradient_accumulation_steps: number;
  dataload_workers: number;
  save_model_per_num_epoch: number;
}

/**
 * Request body for creating a training job
 */
export interface CreateTrainingRequest {
  job_name: string;
  config: Partial<TrainConfig>;
}

/**
 * Response from POST /api/v1/projects/{id}/training
 */
export interface CreateTrainingResponse {
  message: string;
  task_id: string;
  state: TrainingState;
}

/**
 * Response from GET /api/v1/projects/{id}/training/current
 */
export interface CurrentTrainingResponse {
  message: string;
  state: TrainingState | null;
}

/**
 * Response from GET /api/v1/projects/{id}/training
 */
export interface ListTrainingStatesResponse {
  states: TrainingState[];
  count: number;
}

/**
 * Response from GET /api/v1/projects/{id}/training/{job_id}
 */
export interface GetTrainingStateResponse {
  state: TrainingState;
}

/**
 * Response from DELETE /api/v1/projects/{id}/training/{job_id}
 */
export interface DeleteTrainingResponse {
  message: string;
  job_id: string;
}

/**
 * Response from POST /api/v1/projects/{id}/training/batch-delete
 */
export interface BatchDeleteTrainingResponse {
  message: string;
  deleted_count: number;
  failed_count: number;
  deleted_ids: string[];
  failed_ids: string[];
}

/**
 * Training metrics data point
 */
export interface MetricDataPoint {
  step: number;
  value: number;
  wall_time: number;
}

/**
 * Loss metrics from TensorBoard
 */
export interface LossMetrics {
  train_loss: MetricDataPoint[];
  train_diffusion_loss: MetricDataPoint[];
  train_ce_loss: MetricDataPoint[];
  epoch_loss: MetricDataPoint[];
  epoch_diffusion_loss: MetricDataPoint[];
  epoch_ce_loss: MetricDataPoint[];
}

/**
 * Timing metrics from TensorBoard
 */
export interface TimingMetrics {
  step_time: MetricDataPoint[];
  steps_per_second: MetricDataPoint[];
  epoch_time: MetricDataPoint[];
}

/**
 * All metrics from TensorBoard
 */
export interface TrainingMetrics {
  loss: LossMetrics;
  learning_rate: MetricDataPoint[];
  timing: TimingMetrics;
  available_tags?: string[];
}

/**
 * Response from GET /api/v1/projects/{id}/training/{job_id}/metrics
 */
export interface GetTrainingMetricsResponse {
  message: string;
  job_id: string;
  metrics: TrainingMetrics;
}

/**
 * Default training configuration values
 */
export const DEFAULT_TRAIN_CONFIG: Partial<TrainConfig> = {
  lora_name: 'vibevoice_lora',
  epochs: 10,
  batch_size: 1,
  learning_rate: 1e-4,
  output_dir: './lora_output',
  multiplier: 1.0,
  lora_dim: 4,
  lora_alpha: null,
  lora_dropout: null,
  number_of_layers: 0,
  dtype: 'bfloat16',
  optimizer_type: 'AdamW8bit',
  optimizer_args: null,
  seeds: 42,
  dataset_repeats: 1,
  speech_compress_ratio: 3200,
  semantic_dim: 128,
  diffusion_loss_weight: 10.4,
  ce_loss_weight: 0.004,
  device: 'cuda',
  gradient_accumulation_steps: 16,
  dataload_workers: 2,
  save_model_per_num_epoch: 10,
};
