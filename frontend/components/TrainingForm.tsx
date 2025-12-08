'use client';

import React, { useState } from 'react';
import { useTraining } from '@/lib/TrainingContext';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import { useProject } from '@/lib/ProjectContext';
import { useDataset } from '@/lib/DatasetContext';
import type { CreateTrainingRequest, TrainConfig, OptimizerType, TrainingDtype } from '@/types/training';
import { DEFAULT_TRAIN_CONFIG } from '@/types/training';

// Preset information for offloading configurations (same as in GenerationForm)
const PRESET_INFO = {
  balanced: {
    vram_savings: '~5GB',
    slowdown: '~2.0x',
    gpu_layers: 12,
    description: 'Recommended for 12GB+ GPUs (RTX 3060 12GB, 4070)',
  },
  aggressive: {
    vram_savings: '~6GB',
    slowdown: '~2.5x',
    gpu_layers: 8,
    description: 'Recommended for 8-12GB GPUs (RTX 3060 8GB, 4060 8GB)',
  },
  extreme: {
    vram_savings: '~7GB',
    slowdown: '~3.5x',
    gpu_layers: 4,
    description: 'Recommended for 6-8GB GPUs (minimum viable VRAM)',
  },
};

export default function TrainingForm() {
  const { startTraining, loading } = useTraining();
  const { currentProject } = useProject();
  const { datasets } = useDataset();
  const { t } = useLanguage();

  const [jobName, setJobName] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Basic configuration
  const [epochs, setEpochs] = useState(DEFAULT_TRAIN_CONFIG.epochs || 10);
  const [batchSize, setBatchSize] = useState(DEFAULT_TRAIN_CONFIG.batch_size || 1);
  const [learningRate, setLearningRate] = useState(DEFAULT_TRAIN_CONFIG.learning_rate || 1e-4);
  const [loraRank, setLoraRank] = useState(DEFAULT_TRAIN_CONFIG.lora_dim || 4);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');

  // Advanced configuration
  const [loraName, setLoraName] = useState(DEFAULT_TRAIN_CONFIG.lora_name || 'vibevoice_lora');
  const [multiplier, setMultiplier] = useState(DEFAULT_TRAIN_CONFIG.multiplier || 1.0);
  const [loraAlpha, setLoraAlpha] = useState<number | null>(null);
  const [loraDropout, setLoraDropout] = useState<number | null>(null);
  const [optimizer, setOptimizer] = useState<OptimizerType>(DEFAULT_TRAIN_CONFIG.optimizer_type as OptimizerType || 'AdamW8bit');
  const [dtype, setDtype] = useState<TrainingDtype>(DEFAULT_TRAIN_CONFIG.dtype as TrainingDtype || 'bfloat16');
  const [gradientAccumulationSteps, setGradientAccumulationSteps] = useState(DEFAULT_TRAIN_CONFIG.gradient_accumulation_steps || 16);
  const [saveModelPerEpoch, setSaveModelPerEpoch] = useState(DEFAULT_TRAIN_CONFIG.save_model_per_num_epoch || 10);
  const [datasetRepeats, setDatasetRepeats] = useState(DEFAULT_TRAIN_CONFIG.dataset_repeats || 1);
  const [seeds, setSeeds] = useState(Math.floor(Math.random() * (2**64)));

  // Offloading configuration
  const [offloadingEnabled, setOffloadingEnabled] = useState(false);
  const [offloadingMode, setOffloadingMode] = useState<'preset' | 'manual'>('preset');
  const [offloadingPreset, setOffloadingPreset] = useState<'balanced' | 'aggressive' | 'extreme'>('balanced');
  const [manualGpuLayers, setManualGpuLayers] = useState(20);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validation
    if (!jobName.trim()) {
      setError(t('training.validationJobName'));
      return;
    }

    if (!selectedDatasetId) {
      setError(t('training.validationDatasetSelection'));
      return;
    }

    if (epochs <= 0) {
      setError(t('training.validationEpochsPositive'));
      return;
    }

    if (batchSize <= 0) {
      setError(t('training.validationBatchSizePositive'));
      return;
    }

    if (learningRate <= 0) {
      setError(t('training.validationLearningRatePositive'));
      return;
    }

    // Construct dataset path based on workspace structure
    const datasetPath = currentProject
      ? `workspace/${currentProject.id}/datasets/${selectedDatasetId}/datasets.jsonl`
      : null;

    // Calculate number of GPU layers based on offloading configuration
    let numberOfLayers = 0;
    if (offloadingEnabled) {
      if (offloadingMode === 'preset') {
        numberOfLayers = PRESET_INFO[offloadingPreset].gpu_layers;
      } else {
        numberOfLayers = manualGpuLayers;
      }
    }

    const config: Partial<TrainConfig> = {
      lora_name: loraName,
      epochs,
      batch_size: batchSize,
      learning_rate: learningRate,
      lora_dim: loraRank,
      dataset_path: datasetPath,
      multiplier,
      lora_alpha: loraAlpha,
      lora_dropout: loraDropout,
      optimizer_type: optimizer,
      dtype,
      gradient_accumulation_steps: gradientAccumulationSteps,
      save_model_per_num_epoch: saveModelPerEpoch,
      dataset_repeats: datasetRepeats,
      seeds,
      number_of_layers: numberOfLayers,
      // Use project workspace paths
      output_dir: currentProject ? `workspace/${currentProject.id}/lora_output` : './lora_output',
    };

    const request: CreateTrainingRequest = {
      job_name: jobName,
      config,
    };

    try {
      const state = await startTraining(request);
      setSuccess(t('training.startSuccess').replace('{jobId}', state.task_id));

      // Reset form after 3 seconds
      setTimeout(() => {
        setSuccess(null);
        setJobName('');
        setSelectedDatasetId('');
      }, 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('training.startError');
      setError(errorMessage);
    }
  };

  const generateRandomSeed = () => {
    const randomSeed = Math.floor(Math.random() * 1000000);
    setSeeds(randomSeed);
  };

  return (
    <div className="border border-gray-300 rounded-lg p-6 bg-white">
      <h2 className="text-xl font-semibold mb-4">{t('training.startNewTraining')}</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Job Name */}
        <div>
          <label htmlFor="job_name" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.jobName')} <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="job_name"
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            placeholder={t('training.jobNamePlaceholder')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        {/* Dataset Selection */}
        <div>
          <label htmlFor="dataset_selection" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.selectDataset')} <span className="text-red-500">*</span>
          </label>
          <select
            id="dataset_selection"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">{t('training.selectDatasetPlaceholder')}</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} {dataset.description && `(${dataset.description})`}
              </option>
            ))}
          </select>
          {datasets.length === 0 && (
            <p className="text-xs text-amber-600 mt-1">
              {t('training.noDatasetsAvailable')}
            </p>
          )}
          {datasets.length > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              {t('training.selectDatasetDescription')}
            </p>
          )}
        </div>

        {/* Epochs */}
        <div>
          <label htmlFor="epochs" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.epochs')} <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="epochs"
            value={epochs}
            onChange={(e) => setEpochs(parseInt(e.target.value) || 0)}
            min="1"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            {t('training.epochsDescription')}
          </p>
        </div>

        {/* Batch Size */}
        <div>
          <label htmlFor="batch_size" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.batchSize')} <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="batch_size"
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value) || 0)}
            min="1"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            {t('training.batchSizeDescription')}
          </p>
        </div>

        {/* Learning Rate */}
        <div>
          <label htmlFor="learning_rate" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.learningRate')} <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="learning_rate"
            value={learningRate}
            onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0)}
            step="0.0001"
            min="0.0001"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            {t('training.learningRateDescription')}
          </p>
        </div>

        {/* LoRA Rank */}
        <div>
          <label htmlFor="lora_rank" className="block text-sm font-medium text-gray-700 mb-1">
            {t('training.loraRank')} <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="lora_rank"
            value={loraRank}
            onChange={(e) => setLoraRank(parseInt(e.target.value) || 0)}
            min="1"
            max="128"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            {t('training.loraRankDescription')}
          </p>
        </div>

        {/* Advanced Settings Toggle */}
        <div className="border-t border-gray-200 pt-4">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            <svg
              className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            {showAdvanced ? t('training.hideAdvanced') : t('training.showAdvanced')}
          </button>
        </div>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="space-y-4 border border-gray-300 rounded-lg p-4 bg-gray-50">
            {/* LoRA Name */}
            <div>
              <label htmlFor="lora_name" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.loraName')}
              </label>
              <input
                type="text"
                id="lora_name"
                value={loraName}
                onChange={(e) => setLoraName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Optimizer */}
            <div>
              <label htmlFor="optimizer" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.optimizer')}
              </label>
              <select
                id="optimizer"
                value={optimizer}
                onChange={(e) => setOptimizer(e.target.value as OptimizerType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="AdamW8bit">AdamW8bit ({t('training.recommended')})</option>
                <option value="AdamW">AdamW</option>
              </select>
            </div>

            {/* Data Type */}
            <div>
              <label htmlFor="dtype" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.dtype')}
              </label>
              <select
                id="dtype"
                value={dtype}
                onChange={(e) => setDtype(e.target.value as TrainingDtype)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="bfloat16">bfloat16 ({t('training.recommended')})</option>
                <option value="float8_e4m3fn">float8_e4m3fn</option>
              </select>
            </div>

            {/* Gradient Accumulation Steps */}
            <div>
              <label htmlFor="grad_accum" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.gradientAccumulationSteps')}
              </label>
              <input
                type="number"
                id="grad_accum"
                value={gradientAccumulationSteps}
                onChange={(e) => setGradientAccumulationSteps(parseInt(e.target.value) || 0)}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                {t('training.gradientAccumulationDescription')}
              </p>
            </div>

            {/* Save Model Per Epoch */}
            <div>
              <label htmlFor="save_per_epoch" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.saveModelPerEpoch')}
              </label>
              <input
                type="number"
                id="save_per_epoch"
                value={saveModelPerEpoch}
                onChange={(e) => setSaveModelPerEpoch(parseInt(e.target.value) || 0)}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                {t('training.saveModelPerEpochDescription')}
              </p>
            </div>

            {/* Dataset Repeats */}
            <div>
              <label htmlFor="dataset_repeats" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.datasetRepeats')}
              </label>
              <input
                type="number"
                id="dataset_repeats"
                value={datasetRepeats}
                onChange={(e) => setDatasetRepeats(parseInt(e.target.value) || 0)}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Random Seed */}
            <div>
              <label htmlFor="seeds" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.randomSeed')}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  id="seeds"
                  value={seeds}
                  onChange={(e) => setSeeds(parseInt(e.target.value) || 0)}
                  min="0"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={generateRandomSeed}
                  className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  title={t('training.generateRandomSeed')}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 512 512"
                    className="w-5 h-5"
                  >
                    <path
                      d="M302.87 255.5a47.37 47.37 0 1 1-47.37-47.37 47.37 47.37 0 0 1 47.37 47.37zM128.5 81.18a47.37 47.37 0 1 0 47.41 47.32 47.37 47.37 0 0 0-47.41-47.32zm253.91 0a47.37 47.37 0 1 0 47.41 47.32 47.37 47.37 0 0 0-47.32-47.32zM128.5 335.09a47.37 47.37 0 1 0 47.41 47.41 47.37 47.37 0 0 0-47.41-47.41zm253.91 0a47.37 47.37 0 1 0 47.41 47.41 47.37 47.37 0 0 0-47.32-47.41zm102 92.93a56.48 56.48 0 0 1-56.39 56.48h-344a56.48 56.48 0 0 1-56.52-56.48v-344A56.48 56.48 0 0 1 83.98 27.5h344a56.48 56.48 0 0 1 56.52 56.48zm-20-344a36.48 36.48 0 0 0-36.39-36.52h-344A36.48 36.48 0 0 0 47.5 83.98v344a36.48 36.48 0 0 0 36.48 36.52h344a36.48 36.48 0 0 0 36.52-36.48z"
                      fill="currentColor"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Offloading Configuration Section */}
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center gap-2 mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path fillRule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
                <h3 className="text-sm font-medium text-gray-700">{t('generation.offloadingVramOptimization')}</h3>
              </div>

              {/* Enable Checkbox */}
              <label className="flex items-center gap-2 mb-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={offloadingEnabled}
                  onChange={(e) => setOffloadingEnabled(e.target.checked)}
                  className="w-4 h-4 text-blue-500 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">{t('generation.enableOffloading')}</span>
              </label>

              {offloadingEnabled && (
                <>
                  {/* Mode Selection (Preset vs Manual) */}
                  <div className="mb-4 space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        value="preset"
                        checked={offloadingMode === 'preset'}
                        onChange={(e) => setOffloadingMode(e.target.value as 'preset' | 'manual')}
                        className="w-4 h-4 text-blue-500 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">{t('generation.presetRecommended')}</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        value="manual"
                        checked={offloadingMode === 'manual'}
                        onChange={(e) => setOffloadingMode(e.target.value as 'preset' | 'manual')}
                        className="w-4 h-4 text-blue-500 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">{t('generation.manualAdvanced')}</span>
                    </label>
                  </div>

                  {/* Preset Dropdown */}
                  {offloadingMode === 'preset' && (
                    <div>
                      <label htmlFor="offloadingPreset" className="block text-sm font-medium text-gray-700 mb-1">
                        {t('generation.presetConfiguration')}
                      </label>
                      <select
                        id="offloadingPreset"
                        value={offloadingPreset}
                        onChange={(e) => setOffloadingPreset(e.target.value as 'balanced' | 'aggressive' | 'extreme')}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="balanced">{t('generation.balanced')}</option>
                        <option value="aggressive">{t('generation.aggressive')}</option>
                        <option value="extreme">{t('generation.extreme')}</option>
                      </select>

                      {/* Info card for selected preset */}
                      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="text-sm space-y-1">
                          <div className="font-medium text-blue-900">
                            {t(`generation.${offloadingPreset}Configuration`)}
                          </div>
                          <div className="text-blue-800">
                            <strong>{t('generation.gpuLayers')}:</strong> {PRESET_INFO[offloadingPreset].gpu_layers} / 28
                          </div>
                          <div className="text-blue-800">
                            <strong>{t('generation.vramSavings')}:</strong> {PRESET_INFO[offloadingPreset].vram_savings}
                          </div>
                          <div className="text-blue-800">
                            <strong>{t('generation.speed')}:</strong> {PRESET_INFO[offloadingPreset].slowdown} {t('generation.slowerThanNoOffloading')}
                          </div>
                          <div className="text-blue-700 text-xs mt-2">
                            {t(`generation.recommendedFor${offloadingPreset === 'balanced' ? '12GbGpus' : offloadingPreset === 'aggressive' ? '8to12GbGpus' : '6to8GbGpus'}`)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Manual Slider */}
                  {offloadingMode === 'manual' && (
                    <div>
                      <label htmlFor="manualGpuLayers" className="block text-sm font-medium text-gray-700 mb-1">
                        {t('generation.gpuLayers')}: {manualGpuLayers}
                      </label>
                      <input
                        type="range"
                        id="manualGpuLayers"
                        min="1"
                        max="28"
                        value={manualGpuLayers}
                        onChange={(e) => setManualGpuLayers(parseInt(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>1 ({t('generation.moreVramSavings')})</span>
                        <span>28 ({t('generation.lessVramSavings')})</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        {t('generation.fewerGpuLayersInfo')}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Multiplier */}
            <div>
              <label htmlFor="multiplier" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.multiplier')}
              </label>
              <input
                type="number"
                id="multiplier"
                value={multiplier}
                onChange={(e) => setMultiplier(parseFloat(e.target.value) || 0)}
                step="0.1"
                min="0.1"
                max="2.0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* LoRA Alpha (Optional) */}
            <div>
              <label htmlFor="lora_alpha" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.loraAlpha')} ({t('training.optional')})
              </label>
              <input
                type="number"
                id="lora_alpha"
                value={loraAlpha || ''}
                onChange={(e) => setLoraAlpha(e.target.value ? parseFloat(e.target.value) : null)}
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('training.autoCalculated')}
              />
            </div>

            {/* LoRA Dropout (Optional) */}
            <div>
              <label htmlFor="lora_dropout" className="block text-sm font-medium text-gray-700 mb-1">
                {t('training.loraDropout')} ({t('training.optional')})
              </label>
              <input
                type="number"
                id="lora_dropout"
                value={loraDropout || ''}
                onChange={(e) => setLoraDropout(e.target.value ? parseFloat(e.target.value) : null)}
                step="0.01"
                min="0"
                max="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('training.noneByDefault')}
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">{success}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || datasets.length === 0}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? t('training.startingTraining') : t('training.startTraining')}
        </button>
        {datasets.length === 0 && (
          <p className="text-sm text-amber-600 text-center mt-2">
            {t('training.createDatasetFirst')}
          </p>
        )}
      </form>
    </div>
  );
}
