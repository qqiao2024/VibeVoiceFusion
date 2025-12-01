'use client';

import React from 'react';
import { useTraining } from '@/lib/TrainingContext';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import { TrainingStatus } from '@/types/training';

function CurrentTraining() {
  const { currentJob } = useTraining();
  const { t } = useLanguage();

  if (!currentJob) {
    return null;
  }

  const getStatusColor = (status: TrainingStatus): string => {
    switch (status) {
      case TrainingStatus.COMPLETED:
        return 'bg-green-100 text-green-800 border-green-300';
      case TrainingStatus.FAILED:
      case TrainingStatus.CANCELLED:
        return 'bg-red-100 text-red-800 border-red-300';
      case TrainingStatus.PENDING:
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case TrainingStatus.INITIALIZING:
      case TrainingStatus.TRAINING:
      case TrainingStatus.SAVING:
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusLabel = (status: TrainingStatus): string => {
    return t(`training.status${status.charAt(0).toUpperCase() + status.slice(1)}`);
  };

  const isActive = [
    TrainingStatus.PENDING,
    TrainingStatus.INITIALIZING,
    TrainingStatus.TRAINING,
    TrainingStatus.SAVING
  ].includes(currentJob.status);

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  // Render status-specific details
  const renderStatusDetails = () => {
    const metrics = currentJob.metrics;

    // TRAINING phase - show live metrics
    if (currentJob.status === TrainingStatus.TRAINING && metrics) {
      const progressPercentage = (metrics.current_epoch / metrics.total_epochs) * 100;

      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.liveMetrics')}</label>

          {/* Progress Bar */}
          <div className="bg-white bg-opacity-50 rounded p-3">
            <div className="flex justify-between text-xs mb-1">
              <span>{t('training.progress')}</span>
              <span className="font-semibold">{progressPercentage.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 bg-opacity-50 rounded-full h-2">
              <div
                className="bg-current h-2 rounded-full transition-all"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            <div className="flex justify-between text-xs mt-1 opacity-75">
              <span>{t('training.epoch')} {metrics.current_epoch} / {metrics.total_epochs}</span>
              <span>{t('training.step')} {metrics.current_step.toLocaleString()} / {metrics.total_steps.toLocaleString()}</span>
            </div>
          </div>

          {/* Loss Metrics */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">📉 {t('training.lossMetrics')}</p>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <p className="text-2xl font-bold">{metrics.current_loss.toFixed(4)}</p>
                <p className="text-xs opacity-75 mt-1">{t('training.totalLoss')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">{metrics.current_ce_loss.toFixed(4)}</p>
                <p className="text-xs opacity-75 mt-1">{t('training.ceLoss')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">{metrics.current_diffusion_loss.toFixed(4)}</p>
                <p className="text-xs opacity-75 mt-1">{t('training.diffusionLoss')}</p>
              </div>
            </div>
          </div>

          {/* Timing Information */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">⏱️ {t('training.timingInfo')}</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center">
                <p className="text-xl font-bold">{formatDuration(metrics.elapsed_seconds)}</p>
                <p className="text-xs opacity-75 mt-1">{t('training.elapsed')}</p>
              </div>
              {metrics.estimated_remaining_seconds !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(metrics.estimated_remaining_seconds)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.remaining')}</p>
                </div>
              )}
              {metrics.avg_step_time !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{metrics.avg_step_time.toFixed(2)}s</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.avgStepTime')}</p>
                </div>
              )}
              {metrics.avg_epoch_time !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(metrics.avg_epoch_time)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.avgEpochTime')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Learning Rate */}
          <div className="bg-white bg-opacity-50 rounded p-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium opacity-75">{t('training.learningRate')}</span>
              <span className="text-sm font-bold">{metrics.learning_rate.toExponential(2)}</span>
            </div>
          </div>

          {/* TensorBoard Metrics (if available) */}
          {metrics.tensorboard_metrics && Object.keys(metrics.tensorboard_metrics).length > 0 && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-2 opacity-75">📊 {t('training.tensorboardMetrics')}</p>
              <div className="space-y-1">
                {Object.entries(metrics.tensorboard_metrics).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="opacity-75">{key}:</span>
                    <span className="font-semibold">{typeof value === 'number' ? value.toFixed(4) : value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    // COMPLETED phase - show final results
    if (currentJob.status === TrainingStatus.COMPLETED) {
      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.finalResults')}</label>

          {/* Final Loss Metrics */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">📉 {t('training.finalLossValues')}</p>
            <div className="grid grid-cols-3 gap-3">
              {currentJob.final_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentJob.final_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalLoss')}</p>
                </div>
              )}
              {currentJob.final_ce_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentJob.final_ce_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalCELoss')}</p>
                </div>
              )}
              {currentJob.final_diffusion_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentJob.final_diffusion_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalDiffusionLoss')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Training Summary */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">📈 {t('training.trainingSummary')}</p>
            <div className="grid grid-cols-3 gap-3">
              {currentJob.total_steps !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{currentJob.total_steps.toLocaleString()}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalSteps')}</p>
                </div>
              )}
              {currentJob.total_epochs !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{currentJob.total_epochs}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalEpochs')}</p>
                </div>
              )}
              {currentJob.total_training_time !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(currentJob.total_training_time)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalTime')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Saved LoRA Files */}
          {currentJob.saved_lora_files.length > 0 && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-2 opacity-75">
                💾 {t('training.savedLoRAFiles').replace('{count}', currentJob.saved_lora_files.length.toString())}
              </p>
              <div className="space-y-1">
                {currentJob.saved_lora_files.map((file, idx) => (
                  <div key={idx} className="text-xs font-mono bg-white bg-opacity-50 p-2 rounded">
                    {file}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    // FAILED phase - show error
    if (currentJob.status === TrainingStatus.FAILED && currentJob.error_message) {
      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.errorInformation')}</label>
          <div className="bg-white bg-opacity-90 rounded p-4">
            <pre className="text-xs whitespace-pre-wrap">{currentJob.error_message}</pre>
          </div>
        </div>
      );
    }

    // INITIALIZING or PENDING phase
    return (
      <div className="space-y-3">
        <div className="bg-white bg-opacity-50 rounded p-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current mx-auto mb-3"></div>
          <p className="text-sm font-medium opacity-75">
            {currentJob.status === TrainingStatus.INITIALIZING
              ? t('training.initializingMessage')
              : t('training.pendingMessage')}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div
      className={`border-2 rounded-lg p-6 shadow-lg ${getStatusColor(
        currentJob.status
      )}`}
    >
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold flex items-center gap-2">
            {isActive && (
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-current"></span>
              </span>
            )}
            {t('training.currentTraining')}
          </h2>
          <span className="px-3 py-1 rounded-full text-xs font-semibold border-2">
            {getStatusLabel(currentJob.status)}
          </span>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{t('training.jobName')}:</span>
            <span className="text-sm">{currentJob.job_name}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{t('training.jobId')}:</span>
            <span className="text-xs font-mono">{currentJob.job_id}</span>
          </div>
        </div>
      </div>

      {renderStatusDetails()}

      {/* Configuration Details */}
      <div className="mt-4 pt-4 border-t border-current border-opacity-30">
        <label className="text-sm font-medium opacity-75 block mb-2">{t('training.configuration')}</label>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.epochs')}:</span>
            <span className="font-semibold">{currentJob.config.epochs}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.batchSize')}:</span>
            <span className="font-semibold">{currentJob.config.batch_size}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.learningRate')}:</span>
            <span className="font-semibold">{currentJob.config.learning_rate.toExponential(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.loraRank')}:</span>
            <span className="font-semibold">{currentJob.config.lora_dim}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.optimizer')}:</span>
            <span className="font-semibold">{currentJob.config.optimizer_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.dtype')}:</span>
            <span className="font-semibold">{currentJob.config.dtype}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Export with React.memo to prevent unnecessary re-renders
export default React.memo(CurrentTraining);
