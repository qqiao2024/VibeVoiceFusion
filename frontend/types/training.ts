/**
 * Training types for Fine-tuning Training API
 */

/**
 * Training status enum
 */
export enum TrainingStatus {
  PENDING = 'pending',
  INITIALIZING = 'initializing',
  TRAINING = 'training',
  SAVING = 'saving',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

/**
 * Optimizer types supported
 */
export type OptimizerType = 'AdamW' | 'AdamW8bit';

/**
 * Model dtype options for training
 */
export type TrainingDtype = 'bfloat16' | 'float8_e4m3fn';

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
 * Live training metrics during training
 */
export interface TrainingMetrics {
  // Progress
  current_step: number;
  current_epoch: number;
  total_steps: number;
  total_epochs: number;

  // Losses
  current_loss: number;
  current_ce_loss: number;
  current_diffusion_loss: number;

  // Timing
  elapsed_seconds: number;
  estimated_remaining_seconds: number | null;
  avg_step_time: number | null;
  avg_epoch_time: number | null;

  // Learning rate
  learning_rate: number;

  // TensorBoard metrics (if available)
  tensorboard_metrics?: {
    [key: string]: number;
  };
}

/**
 * Training job representing a single training run
 */
export interface TrainingJob {
  job_id: string;
  job_name: string;
  status: TrainingStatus;
  config: TrainConfig;

  // Timestamps
  created_at: string;
  started_at: string | null;
  completed_at: string | null;

  // Live metrics (during training)
  metrics: TrainingMetrics | null;

  // Final results (after completion)
  final_loss: number | null;
  final_ce_loss: number | null;
  final_diffusion_loss: number | null;
  total_steps: number | null;
  total_epochs: number | null;
  total_training_time: number | null;

  // Saved models
  saved_lora_files: string[];

  // Error info (if failed)
  error_message: string | null;

  // Project info
  project_id: string;
}

/**
 * Request body for creating a training job
 */
export interface CreateTrainingRequest {
  job_name: string;
  config: Partial<TrainConfig>;
}

/**
 * Response from POST /training
 */
export interface CreateTrainingResponse {
  message: string;
  job_id: string;
  job: TrainingJob;
}

/**
 * Response from GET /training/current
 */
export interface CurrentTrainingResponse {
  message: string;
  job: TrainingJob | null;
}

/**
 * Response from GET /training
 */
export interface ListTrainingJobsResponse {
  jobs: TrainingJob[];
  count: number;
}

/**
 * Response from GET /training/:job_id
 */
export interface GetTrainingJobResponse {
  job: TrainingJob;
}

/**
 * Response from DELETE /training/:job_id
 */
export interface DeleteTrainingJobResponse {
  message: string;
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
