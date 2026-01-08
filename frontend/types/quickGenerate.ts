/**
 * Quick Generate types for Quick Voice Generation API
 */

import { InferencePhase, ModelDtype, OffloadingConfig } from './generation';

/**
 * Detected mode for quick generate text
 */
export type QuickGenerateMode = 'dialogue' | 'narration';

/**
 * Individual generation item for multi-generation
 */
export interface QuickGenerateItem {
  batch_index: number;
  audio_path: string;
  seeds: number;
  generation_time: number;
  audio_duration_seconds?: number;
  real_time_factor?: number;
}

/**
 * Quick generate details
 */
export interface QuickGenerateDetails {
  preprocessing_duration?: number;
  generation_items: QuickGenerateItem[];
  offloading_config?: OffloadingConfig;
}

/**
 * Quick generate metadata from backend
 */
export interface QuickGenerate {
  request_id: string;
  voice_files: string[];  // Paths to uploaded voice files (up to 4)
  voice_file?: string;    // Backward compatibility - first voice file
  text: string;
  detected_mode: QuickGenerateMode;
  status: InferencePhase;
  seeds: number;
  batch_size: number;
  cfg_scale: number;
  model_dtype: ModelDtype;
  attn_implementation: string;
  created_at: string;
  updated_at: string;
  output_files: string[];
  percentage?: number;
  current_batch_index?: number;
  details?: QuickGenerateDetails;
  error_message?: string;
  completed_at?: string;
  offloading?: OffloadingConfig;
  is_multi_generation: boolean;
  text_preview?: string;
}

/**
 * Request body for starting quick generation
 */
export interface StartQuickGenerateRequest {
  voice_file: File;
  text: string;
  seeds?: number;
  batch_size?: number;
  cfg_scale?: number;
  model_dtype?: ModelDtype;
  attn_implementation?: string;
  offloading?: OffloadingConfig;
}

/**
 * Response from POST /quick-generate
 */
export interface StartQuickGenerateResponse {
  message: string;
  request_id: string;
  detected_mode: QuickGenerateMode;
  status: string;
}

/**
 * Response from GET /quick-generate/current
 */
export interface CurrentQuickGenerateResponse {
  message: string;
  generation: QuickGenerate | null;
}

/**
 * Quick generate history item (subset of QuickGenerate for list display)
 */
export interface QuickGenerateHistoryItem {
  request_id: string;
  status: string;
  detected_mode: QuickGenerateMode;
  text_preview?: string;
  batch_size: number;
  created_at: string;
  completed_at?: string;
}

/**
 * Response from GET /quick-generate/history
 */
export interface QuickGenerateHistoryResponse {
  generations: QuickGenerateHistoryItem[];
  count: number;
  total: number;
}

/**
 * Check if a quick generation is multi-generation
 */
export function isQuickMultiGeneration(quickGen: QuickGenerate): boolean {
  return quickGen.is_multi_generation || (quickGen.batch_size > 1);
}

/**
 * Get completed items count for quick generation
 */
export function getQuickCompletedItemsCount(quickGen: QuickGenerate): number {
  if (!quickGen.details?.generation_items) return 0;
  return quickGen.details.generation_items.filter(
    item => item.audio_path && item.audio_path.length > 0
  ).length;
}

/**
 * Calculate aggregate statistics for quick multi-generation
 */
export function getQuickMultiGenerationStats(quickGen: QuickGenerate): {
  totalAudioDuration: number;
  totalGenerationTime: number;
  averageRTF: number;
  averageDuration: number;
  completedCount: number;
  totalCount: number;
} | null {
  if (!isQuickMultiGeneration(quickGen)) return null;

  const items = quickGen.details?.generation_items || [];
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
    totalCount: quickGen.batch_size || items.length
  };
}
