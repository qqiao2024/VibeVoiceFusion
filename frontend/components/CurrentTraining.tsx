'use client';

import React from 'react';
import { useTraining } from '@/lib/TrainingContext';
import { useProject } from '@/lib/ProjectContext';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import TrainingMetricsChart from '@/components/TrainingMetricsChart';
import type { TrainingStatus } from '@/types/training';

function CurrentTraining() {
  const { currentState, clearCurrentState } = useTraining();
  const { currentProject } = useProject();
  const { t } = useLanguage();

  if (!currentState || !currentProject) {
    return null;
  }

  const handleStartNewTraining = () => {
    clearCurrentState();
  };

  const getStatusColor = (status: TrainingStatus): string => {
    switch (status) {
      case 'Completed':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'Failed':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'Prepare':
        return 'bg-gray-100 text-gray-800 border-gray-300';
      case 'Training':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusLabel = (status: TrainingStatus): string => {
    const statusMap: Record<TrainingStatus, string> = {
      'Prepare': 'training.statusPending',
      'Training': 'training.statusTraining',
      'Completed': 'training.statusCompleted',
      'Failed': 'training.statusFailed',
    };
    return t(statusMap[status] || 'training.statusPending');
  };

  const isActive = ['Prepare', 'Training'].includes(currentState.status);

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

  // Calculate metrics from state
  const elapsedSeconds = currentState.start_time && currentState.current_timestamp
    ? (new Date(currentState.current_timestamp).getTime() - new Date(currentState.start_time).getTime()) / 1000
    : 0;

  // Calculate estimated remaining time
  // Formula: estimated_total_elpase - (current_timestamp - start_time)
  const estimatedRemaining = currentState.estimated_total_elpase && currentState.start_time
    ? Math.max(0, currentState.estimated_total_elpase - (Date.now() - new Date(currentState.start_time).getTime()) / 1000)
    : null;

  // Render status-specific details
  const renderStatusDetails = () => {
    // TRAINING phase - show live metrics
    if (currentState.status === 'Training' && currentState.current_epoch !== null && currentState.total_epochs !== null) {
      // Calculate smooth progress that moves continuously throughout training
      // Uses steps_per_epoch and steps_in_epoch for accurate intra-epoch progress
      let progressPercentage = 0;

      if (currentState.current_epoch !== null &&
          currentState.total_epochs !== null &&
          currentState.total_epochs > 0) {

        // Calculate number of completed epochs (epochs that have finished)
        const completedEpochs = Math.max(0, currentState.current_epoch - 1);

        // Calculate progress within the current epoch
        let progressInCurrentEpoch = 0;

        if (currentState.steps_per_epoch !== null &&
            currentState.steps_per_epoch > 0 &&
            currentState.steps_in_epoch !== null) {
          // BEST: We know steps_per_epoch, so we can calculate exact progress within epoch
          progressInCurrentEpoch = currentState.steps_in_epoch / currentState.steps_per_epoch;
        } else if (currentState.current_epoch === 1 &&
                   currentState.steps_in_epoch !== null &&
                   currentState.steps_in_epoch > 0) {
          // FIRST EPOCH EDGE CASE: steps_per_epoch is still 0 during first epoch
          // We don't know total steps per epoch yet, so estimate conservatively
          // Show progress within first epoch but cap at 90% to avoid exceeding epoch boundary
          // This provides visual feedback that training is progressing
          const estimatedMaxStepsInFirstEpoch = currentState.steps_in_epoch * 1.5; // Assume we're at least 67% through
          progressInCurrentEpoch = Math.min(0.9, currentState.steps_in_epoch / estimatedMaxStepsInFirstEpoch);
        } else if (currentState.current_step !== null &&
                   currentState.estimated_total_steps !== null &&
                   currentState.estimated_total_steps > 0) {
          // FALLBACK: Use global step progress
          progressPercentage = (currentState.current_step / currentState.estimated_total_steps) * 100;
        } else {
          // LAST RESORT: Just use epoch boundaries (no intra-epoch progress)
          progressInCurrentEpoch = 0;
        }

        // If we calculated progress using epochs (not global steps)
        if (progressPercentage === 0) {
          // Total progress = (completed_epochs + progress_in_current_epoch) / total_epochs
          progressPercentage = ((completedEpochs + progressInCurrentEpoch) / currentState.total_epochs) * 100;
        }
      }

      // Clamp to 0-99.9% (never show 100% until status becomes "Completed")
      progressPercentage = Math.min(99.9, Math.max(0, progressPercentage));

      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.liveMetrics')}</label>

          {/* Progress Bar - tqdm style */}
          <div className="bg-white bg-opacity-50 rounded p-3">
            {/* Progress bar with inline metrics */}
            <div className="w-full bg-gray-200 bg-opacity-50 rounded-full h-6 relative overflow-hidden">
              <div
                className="bg-current h-6 rounded-full transition-all flex items-center"
                style={{ width: `${progressPercentage}%` }}
              >
                {progressPercentage > 15 && (
                  <span className="text-white text-xs font-semibold ml-2">
                    {progressPercentage.toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
            {/* Inline metrics display - tqdm style */}
            <div className="mt-2 text-xs font-mono space-y-1">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-semibold text-blue-900">
                  {t('training.epoch')} {currentState.current_epoch}/{currentState.total_epochs}
                </span>
                {currentState.current_step !== null && currentState.estimated_total_steps !== null && (
                  <>
                    <span className="text-gray-400">│</span>
                    <span className="font-semibold text-blue-900">
                      {t('training.step')} {currentState.current_step.toLocaleString()}/{currentState.estimated_total_steps.toLocaleString()}
                    </span>
                  </>
                )}
                {currentState.current_loss !== null && (
                  <>
                    <span className="text-gray-400">│</span>
                    <span className="font-semibold text-green-900">
                      Loss: {currentState.current_loss.toFixed(4)}
                    </span>
                  </>
                )}
              </div>
              {/* Additional loss breakdown if available */}
              {(currentState.current_ce_loss !== null || currentState.current_diffusion_loss !== null) && (
                <div className="flex items-center gap-3 flex-wrap text-gray-600">
                  {currentState.current_ce_loss !== null && (
                    <span>CE: {currentState.current_ce_loss.toFixed(4)}</span>
                  )}
                  {currentState.current_diffusion_loss !== null && (
                    <>
                      {currentState.current_ce_loss !== null && <span className="text-gray-400">│</span>}
                      <span>Diff: {currentState.current_diffusion_loss.toFixed(4)}</span>
                    </>
                  )}
                  {currentState.average_step_time !== null && (
                    <>
                      <span className="text-gray-400">│</span>
                      <span>{currentState.average_step_time.toFixed(2)}s/step</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Loss Metrics */}
          {currentState.current_loss !== null && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-3 opacity-75">📉 {t('training.lossMetrics')}</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentState.current_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalLoss')}</p>
                </div>
                {currentState.current_ce_loss !== null && (
                  <div className="text-center">
                    <p className="text-2xl font-bold">{currentState.current_ce_loss.toFixed(4)}</p>
                    <p className="text-xs opacity-75 mt-1">{t('training.ceLoss')}</p>
                  </div>
                )}
                {currentState.current_diffusion_loss !== null && (
                  <div className="text-center">
                    <p className="text-2xl font-bold">{currentState.current_diffusion_loss.toFixed(4)}</p>
                    <p className="text-xs opacity-75 mt-1">{t('training.diffusionLoss')}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Timing Information */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">⏱️ {t('training.timingInfo')}</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center">
                <p className="text-xl font-bold">{formatDuration(elapsedSeconds)}</p>
                <p className="text-xs opacity-75 mt-1">{t('training.elapsed')}</p>
              </div>
              {estimatedRemaining !== null && estimatedRemaining > 0 && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(estimatedRemaining)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.remaining')}</p>
                </div>
              )}
              {currentState.average_step_time !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{currentState.average_step_time.toFixed(2)}s</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.avgStepTime')}</p>
                </div>
              )}
              {currentState.latest_epoch_elapsed !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(currentState.latest_epoch_elapsed)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.latestEpochTime')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Learning Rate */}
          {currentState.learning_rate !== null && (
            <div className="bg-white bg-opacity-50 rounded p-3">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium opacity-75">{t('training.learningRate')}</span>
                <span className="text-sm font-bold">{currentState.learning_rate.toExponential(2)}</span>
              </div>
            </div>
          )}

          {/* Metrics Charts */}
          {currentState.tensorboard_logdir && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-3 opacity-75">📊 {t('training.trainingMetrics')}</p>
              <TrainingMetricsChart
                projectId={currentProject.id}
                jobId={currentState.task_id}
                autoRefresh={true}
                refreshInterval={5000}
              />
            </div>
          )}
        </div>
      );
    }

    // COMPLETED phase - show final results
    if (currentState.status === 'Completed') {
      const trainingTime = currentState.start_time && currentState.current_timestamp
        ? (new Date(currentState.current_timestamp).getTime() - new Date(currentState.start_time).getTime()) / 1000
        : null;

      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.finalResults')}</label>

          {/* Final Loss Metrics */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">📉 {t('training.finalLossValues')}</p>
            <div className="grid grid-cols-3 gap-3">
              {currentState.current_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentState.current_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalLoss')}</p>
                </div>
              )}
              {currentState.current_ce_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentState.current_ce_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalCELoss')}</p>
                </div>
              )}
              {currentState.current_diffusion_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold">{currentState.current_diffusion_loss.toFixed(4)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.finalDiffusionLoss')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Training Summary */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <p className="text-xs font-medium mb-3 opacity-75">📈 {t('training.trainingSummary')}</p>
            <div className="grid grid-cols-3 gap-3">
              {currentState.current_step !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{currentState.current_step.toLocaleString()}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalSteps')}</p>
                </div>
              )}
              {currentState.current_epoch !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{currentState.current_epoch}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalEpochs')}</p>
                </div>
              )}
              {trainingTime !== null && (
                <div className="text-center">
                  <p className="text-xl font-bold">{formatDuration(trainingTime)}</p>
                  <p className="text-xs opacity-75 mt-1">{t('training.totalTime')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Saved LoRA Files */}
          {currentState.lora_files.length > 0 && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-2 opacity-75">
                💾 {t('training.savedLoRAFiles').replace('{count}', currentState.lora_files.length.toString())}
              </p>
              <div className="space-y-1">
                {currentState.lora_files.map((file, idx) => (
                  <div key={idx} className="text-xs font-mono bg-white bg-opacity-50 p-2 rounded">
                    {file}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metrics Charts (Final Results) */}
          {currentState.tensorboard_logdir && (
            <div className="bg-white bg-opacity-90 rounded p-4">
              <p className="text-xs font-medium mb-3 opacity-75">📊 {t('training.trainingMetrics')}</p>
              <TrainingMetricsChart
                projectId={currentProject.id}
                jobId={currentState.task_id}
                autoRefresh={false}
                refreshInterval={5000}
              />
            </div>
          )}

          {/* Start New Training Button */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <button
              onClick={handleStartNewTraining}
              className="w-full px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-semibold flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
              </svg>
              {t('training.startNewTraining')}
            </button>
          </div>
        </div>
      );
    }

    // FAILED phase - show error
    if (currentState.status === 'Failed' && currentState.error_message) {
      return (
        <div className="space-y-3">
          <label className="text-sm font-medium opacity-75 block">{t('training.errorInformation')}</label>
          <div className="bg-white bg-opacity-90 rounded p-4">
            <pre className="text-xs whitespace-pre-wrap">{currentState.error_message}</pre>
          </div>

          {/* Start New Training Button */}
          <div className="bg-white bg-opacity-90 rounded p-4">
            <button
              onClick={handleStartNewTraining}
              className="w-full px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-semibold flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
              </svg>
              {t('training.startNewTraining')}
            </button>
          </div>
        </div>
      );
    }

    // PREPARE (PENDING) phase
    return (
      <div className="space-y-3">
        <div className="bg-white bg-opacity-50 rounded p-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current mx-auto mb-3"></div>
          <p className="text-sm font-medium opacity-75">
            {t('training.pendingMessage')}
          </p>
        </div>
      </div>
    );
  };

  const isCompleted = currentState.status === 'Completed' || currentState.status === 'Failed';
  const titleKey = isCompleted ? 'training.trainingSummary' : 'training.currentTraining';

  return (
    <div
      className={`border-2 rounded-lg p-6 shadow-lg ${getStatusColor(
        currentState.status
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
            {t(titleKey)}
          </h2>
          <span className="px-3 py-1 rounded-full text-xs font-semibold border-2">
            {getStatusLabel(currentState.status)}
          </span>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{t('training.jobName')}:</span>
            <span className="text-sm">{currentState.job_name}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{t('training.jobId')}:</span>
            <span className="text-xs font-mono">{currentState.task_id}</span>
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
            <span className="font-semibold">{currentState.config.epochs}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.batchSize')}:</span>
            <span className="font-semibold">{currentState.config.batch_size}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.learningRate')}:</span>
            <span className="font-semibold">{currentState.config.learning_rate.toExponential(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.loraRank')}:</span>
            <span className="font-semibold">{currentState.config.lora_dim}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.optimizer')}:</span>
            <span className="font-semibold">{currentState.config.optimizer_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-75">{t('training.dtype')}:</span>
            <span className="font-semibold">{currentState.config.dtype}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Export with React.memo to prevent unnecessary re-renders
export default React.memo(CurrentTraining);
