/**
 * Generation types for Voice Generation API
 */

/**
 * Inference phase enum matching backend InferencePhase
 * Note: Backend currently returns lowercase values
 */
export enum InferencePhase {
  PENDING = 'pending',
  PREPROCESSING = 'preprocessing',
  INFERENCING = 'inferencing',
  SAVING_AUDIO = 'saving_audio',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

/**
 * Model dtype options
 */
export type ModelDtype = 'bf16' | 'float8_e4m3fn';

/**
 * Individual generation item for multi-generation
 * Each item represents one audio file generated in a batch
 */
export interface GenerationItem {
  epoch_idx: number;                    // Batch index (0, 1, 2, ...)
  audio_path: string;                   // Path to generated audio file
  seeds: number;                        // Random seed used for this item
  generation_time: number;              // Time taken for generation in seconds
  prefilling_tokens?: number;           // Number of prefilling tokens
  total_tokens?: number;                // Total number of tokens generated
  generated_tokens?: number;            // Number of tokens generated
  audio_duration_seconds?: number;      // Duration of generated audio
  real_time_factor?: number;            // Real-time factor for generation speed
  current_step?: number;                // Current step in generation process
  total_steps?: number;                 // Total steps in generation process
}

/**
 * Generation details including multi-generation items
 */
export interface GenerationDetails {
  scripts?: string[];
  unique_speaker_names?: string[];
  voice_sample?: string[];
  max_speaker_id?: number;
  preprocessing_duration?: number;
  generation_items?: GenerationItem[];  // List of all generation items for multi-gen
  // Legacy single-generation fields (for backward compatibility)
  generation_time?: number;
  audio_duration_seconds?: number;
  real_time_factor?: number;
  prefilling_tokens?: number;
  generated_tokens?: number;
  total_tokens?: number;
  output_audio_path?: string;
  number_of_segments?: number;
  error?: string;
  current?: number;
  total_step?: number;
  offloading_config?: OffloadingConfig;
  offloading_metrics?: OffloadingMetrics;
}

/**
 * Generation metadata from backend
 */
export interface Generation {
  request_id: string;
  session_id: string;
  session_name: string;
  status: InferencePhase;
  output_filename: string | null;
  percentage: number | null;
  model_dtype: ModelDtype;
  cfg_scale: number | null;
  attn_implementation: string | null;
  seeds: number;
  details: GenerationDetails;
  created_at: string;
  updated_at: string;
  project_id?: string | null;
  project_dir?: string | null;
  lora_model_path?: string | null;      // Path to LoRA model file
  lora_weight?: number;                 // Weight for LoRA model (0, 1]
  // Multi-generation fields
  is_multi_generation?: boolean;        // Flag for multi-generation
  fix_seed?: boolean;                   // Flag to fix the random seed (reserved for future)
  current_batch_index?: number | null;  // Current batch index (0-based)
  batch_size?: number | null;           // Total number of batches
}

/**
 * Offloading configuration mode
 */
export type OffloadingMode = 'preset' | 'manual';

/**
 * Offloading preset options
 */
export type OffloadingPreset = 'balanced' | 'aggressive' | 'extreme';

/**
 * Offloading configuration for generation request
 */
export interface OffloadingConfig {
  enabled: boolean;
  mode: OffloadingMode;
  preset?: OffloadingPreset;      // Required for preset mode
  num_gpu_layers?: number;        // Required for manual mode (1-28)
}

/**
 * Time breakdown for offloading metrics
 */
export interface OffloadingTimeBreakdown {
  pure_computation_ms: number;
  cpu_to_gpu_transfer_ms: number;
  gpu_to_cpu_release_ms: number;
}

/**
 * Offloading metrics returned after generation completes
 */
export interface OffloadingMetrics {
  enabled: boolean;
  gpu_layers: number;
  cpu_layers: number;
  transfer_overhead_ms: number;
  avg_layer_transfer_ms: number;
  overhead_percentage: number;
  time_breakdown: OffloadingTimeBreakdown;
  theoretical_async_savings_ms: number;
  vram_saved_gb: number;
}

/**
 * Request body for creating generation
 */
export interface CreateGenerationRequest {
  dialog_session_id: string;
  seeds?: number;
  cfg_scale?: number;
  model_dtype?: ModelDtype;
  attn_implementation?: string;
  offloading?: OffloadingConfig;  // Optional offloading configuration
  lora_model_path?: string;       // Optional LoRA model file path (full path)
  lora_weight?: number;           // Optional LoRA weight (0, 1], default 1.0
  batch_size?: number;            // Number of generations for multi-gen (1-20, default 1)
}

/**
 * Response from POST /generations
 */
export interface CreateGenerationResponse {
  message: string;
  request_id: string;
  generation: Generation;
}

/**
 * Response from GET /generations/current
 * Note: generation is null when no active generation (200 response, not an error)
 */
export interface CurrentGenerationResponse {
  message: string;
  generation: Generation | null;
}

/**
 * Response from GET /generations
 */
export interface ListGenerationsResponse {
  generations: Generation[];
  count: number;
}

/**
 * Response from GET /generations/:request_id
 */
export interface GetGenerationResponse {
  generation: Generation;
}

/**
 * Helper function to extract offloading configuration from generation.details
 */
export function getOffloadingConfig(generation: Generation): OffloadingConfig | null {
  return generation.details?.offloading_config || null;
}

/**
 * Helper function to extract offloading metrics from generation.details
 */
export function getOffloadingMetrics(generation: Generation): OffloadingMetrics | null {
  return generation.details?.offloading_metrics || null;
}

/**
 * Helper function to extract LoRA display name from full path
 * Converts: /workspace/.../lora_output/abc/model_final.safetensors -> abc/model_final.safetensors
 */
export function getLoraDisplayName(loraPath: string | null | undefined): string | null {
  if (!loraPath) return null;

  // Find lora_output in the path and extract everything after it
  const loraOutputIndex = loraPath.indexOf('lora_output/');
  if (loraOutputIndex !== -1) {
    return loraPath.substring(loraOutputIndex + 'lora_output/'.length);
  }

  // Fallback: get last two path components (lora_name/filename)
  const parts = loraPath.split('/').filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
  }

  // Last fallback: just return the filename
  return parts[parts.length - 1] || loraPath;
}

/**
 * Check if a generation is a multi-generation request
 */
export function isMultiGeneration(generation: Generation): boolean {
  return generation.is_multi_generation === true ||
         (generation.batch_size !== null && generation.batch_size !== undefined && generation.batch_size > 1);
}

/**
 * Get generation items from a generation (handles both multi and single generation)
 */
export function getGenerationItems(generation: Generation): GenerationItem[] {
  return generation.details?.generation_items || [];
}

/**
 * Get completed generation items count
 */
export function getCompletedItemsCount(generation: Generation): number {
  const items = getGenerationItems(generation);
  return items.filter(item => item.audio_path && item.audio_path.length > 0).length;
}

/**
 * Calculate aggregate statistics for multi-generation
 */
export function getMultiGenerationStats(generation: Generation): {
  totalAudioDuration: number;
  totalGenerationTime: number;
  averageRTF: number;
  averageDuration: number;
  completedCount: number;
  totalCount: number;
} | null {
  if (!isMultiGeneration(generation)) return null;

  const items = getGenerationItems(generation);
  if (items.length === 0) return null;

  const completedItems = items.filter(item => item.audio_path && item.audio_path.length > 0);

  const totalAudioDuration = completedItems.reduce(
    (sum, item) => sum + (item.audio_duration_seconds || 0), 0
  );
  const totalGenerationTime = completedItems.reduce(
    (sum, item) => sum + (item.generation_time || 0), 0
  );

  const averageRTF = completedItems.length > 0 && totalGenerationTime > 0
    ? totalAudioDuration / totalGenerationTime
    : 0;
  const averageDuration = completedItems.length > 0
    ? totalAudioDuration / completedItems.length
    : 0;

  return {
    totalAudioDuration,
    totalGenerationTime,
    averageRTF,
    averageDuration,
    completedCount: completedItems.length,
    totalCount: generation.batch_size || items.length
  };
}

/**
 * Get the filename from an audio path
 */
export function getAudioFilename(audioPath: string): string {
  if (!audioPath) return '';
  const parts = audioPath.split('/');
  return parts[parts.length - 1] || audioPath;
}
