'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { useTraining } from '@/lib/TrainingContext';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import type { TrainingState, TrainingStatus } from '@/types/training';
import toast from 'react-hot-toast';

function TrainingHistory() {
  const { states, loading, deleteJob } = useTraining();
  const { t } = useLanguage();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [singleDeleteId, setSingleDeleteId] = useState<string | null>(null);

  const toggleDetails = useCallback((jobId: string) => {
    setExpandedId(prev => prev === jobId ? null : jobId);
  }, []);

  // Memoize pagination calculations
  const paginationData = useMemo(() => {
    const totalPages = Math.ceil(states.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedStates = states.slice(startIndex, endIndex);

    return {
      totalPages,
      startIndex,
      endIndex,
      paginatedStates
    };
  }, [states, currentPage, itemsPerPage]);

  const { totalPages, startIndex, endIndex, paginatedStates } = paginationData;

  // Selection handlers
  const toggleSelection = useCallback((jobId: string) => {
    setSelectedIds(prev => {
      const newSelected = new Set(prev);
      if (newSelected.has(jobId)) {
        newSelected.delete(jobId);
      } else {
        newSelected.add(jobId);
      }
      return newSelected;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds(prev => {
      if (prev.size === paginatedStates.length) {
        return new Set();
      } else {
        return new Set(paginatedStates.map(s => s.task_id));
      }
    });
  }, [paginatedStates]);

  const isAllSelected = paginatedStates.length > 0 && selectedIds.size === paginatedStates.length;
  const isSomeSelected = selectedIds.size > 0 && selectedIds.size < paginatedStates.length;

  // Delete handlers
  const handleDeleteClick = useCallback((jobId: string) => {
    setSingleDeleteId(jobId);
    setShowDeleteDialog(true);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    try {
      if (singleDeleteId) {
        await deleteJob(singleDeleteId);
        toast.success(t('training.deleteSuccess'));
      }
      setShowDeleteDialog(false);
      setSingleDeleteId(null);
    } catch (error) {
      console.error('Delete failed:', error);
      toast.error(error instanceof Error ? error.message : t('training.deleteFailed'));
    }
  }, [singleDeleteId, deleteJob, t]);

  const handleCancelDelete = useCallback(() => {
    setShowDeleteDialog(false);
    setSingleDeleteId(null);
  }, []);

  // Pagination handlers
  const goToPage = useCallback((page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  }, [totalPages]);

  const handleItemsPerPageChange = useCallback((value: number) => {
    setItemsPerPage(value);
    setCurrentPage(1);
  }, []);

  const getStatusColor = (status: TrainingStatus): string => {
    switch (status) {
      case 'Completed':
        return 'bg-green-100 text-green-800';
      case 'Failed':
        return 'bg-red-100 text-red-800';
      case 'Prepare':
        return 'bg-yellow-100 text-yellow-800';
      case 'Training':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: TrainingStatus): string => {
    // Map backend status to translation keys
    const statusMap: Record<TrainingStatus, string> = {
      'Prepare': 'training.statusPending',
      'Training': 'training.statusTraining',
      'Completed': 'training.statusCompleted',
      'Failed': 'training.statusFailed',
    };
    return t(statusMap[status] || 'training.statusPending');
  };

  const formatDate = (isoDate: string): string => {
    return new Date(isoDate).toLocaleString();
  };

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return 'N/A';
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

  // Render training state details
  const renderStateDetails = (state: TrainingState) => {
    const isCompleted = state.status === 'Completed';
    const trainingTime = state.start_time && state.current_timestamp
      ? (new Date(state.current_timestamp).getTime() - new Date(state.start_time).getTime()) / 1000
      : null;

    return (
      <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
        {/* Basic Information */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-gray-600">{t('training.jobId')}</label>
            <p className="text-sm font-mono text-gray-900 break-all">{state.task_id}</p>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">{t('training.jobName')}</label>
            <p className="text-sm text-gray-900">{state.job_name}</p>
          </div>
        </div>

        {/* Final Results (for completed jobs) */}
        {isCompleted && (
          <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4 border border-green-200">
            <p className="text-sm font-semibold text-gray-800 mb-3">📊 {t('training.finalResults')}</p>
            <div className="grid grid-cols-3 gap-4">
              {state.current_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-700">{state.current_loss.toFixed(4)}</p>
                  <p className="text-xs text-gray-600 mt-1">{t('training.finalLoss')}</p>
                </div>
              )}
              {state.current_ce_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-700">{state.current_ce_loss.toFixed(4)}</p>
                  <p className="text-xs text-gray-600 mt-1">{t('training.finalCELoss')}</p>
                </div>
              )}
              {state.current_diffusion_loss !== null && (
                <div className="text-center">
                  <p className="text-2xl font-bold text-purple-700">{state.current_diffusion_loss.toFixed(4)}</p>
                  <p className="text-xs text-gray-600 mt-1">{t('training.finalDiffusionLoss')}</p>
                </div>
              )}
            </div>
            <div className="mt-3 pt-3 border-t border-green-200 grid grid-cols-3 gap-4 text-center text-xs text-gray-600">
              {state.current_step !== null && (
                <div>
                  <p className="font-semibold text-gray-900">{state.current_step.toLocaleString()}</p>
                  <p>{t('training.totalSteps')}</p>
                </div>
              )}
              {state.current_epoch !== null && (
                <div>
                  <p className="font-semibold text-gray-900">{state.current_epoch}</p>
                  <p>{t('training.totalEpochs')}</p>
                </div>
              )}
              {trainingTime !== null && (
                <div>
                  <p className="font-semibold text-gray-900">{formatDuration(trainingTime)}</p>
                  <p>{t('training.totalTime')}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Saved LoRA Files */}
        {state.lora_files.length > 0 && (
          <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
            <p className="text-xs font-semibold text-purple-800 mb-2">
              💾 {t('training.savedLoRAFiles').replace('{count}', state.lora_files.length.toString())}
            </p>
            <div className="space-y-1">
              {state.lora_files.map((file, idx) => (
                <div key={idx} className="text-xs font-mono bg-white p-2 rounded border border-purple-100">
                  {file}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Training Configuration */}
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-2">{t('training.configuration')}</label>
          <div className="grid grid-cols-2 gap-3 bg-gray-50 rounded p-3">
            <div>
              <p className="text-xs text-gray-600">{t('training.epochs')}</p>
              <p className="text-sm font-semibold">{state.config.epochs}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">{t('training.batchSize')}</p>
              <p className="text-sm font-semibold">{state.config.batch_size}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">{t('training.learningRate')}</p>
              <p className="text-sm font-semibold">{state.config.learning_rate}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">{t('training.loraRank')}</p>
              <p className="text-sm font-semibold">{state.config.lora_dim}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">{t('training.optimizer')}</p>
              <p className="text-sm font-semibold">{state.config.optimizer_type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">{t('training.dtype')}</p>
              <p className="text-sm font-semibold">{state.config.dtype}</p>
            </div>
          </div>
        </div>

        {/* Error Information (for failed jobs) */}
        {state.status === 'Failed' && state.error_message && (
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-2">{t('training.errorInformation')}</label>
            <div className="bg-red-50 rounded p-3">
              <pre className="text-xs whitespace-pre-wrap text-red-900">{state.error_message}</pre>
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="bg-gray-50 rounded p-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <p className="text-gray-600">{t('training.created')}</p>
              <p className="font-medium">{formatDate(state.created_at)}</p>
            </div>
            {state.start_time && (
              <div>
                <p className="text-gray-600">{t('training.started')}</p>
                <p className="font-medium">{formatDate(state.start_time)}</p>
              </div>
            )}
            {isCompleted && state.current_timestamp && (
              <div>
                <p className="text-gray-600">{t('training.completed')}</p>
                <p className="font-medium">{formatDate(state.current_timestamp)}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">{t('training.loadingHistory')}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold mb-2">{t('training.trainingHistory')}</h2>
        <p className="text-sm text-gray-600">
          {t('training.totalJobs')
            .replace('{count}', states.length.toString())
            .replace('{plural}', states.length !== 1 ? 's' : '')}
        </p>
      </div>

      {states.length === 0 ? (
        <div className="flex items-center justify-center flex-1 text-gray-500">
          <p>{t('training.noHistory')}</p>
        </div>
      ) : (
        <>
          {/* Select all checkbox */}
          {paginatedStates.length > 0 && (
            <div className="mb-2 flex items-center gap-2 px-2">
              <input
                type="checkbox"
                checked={isAllSelected}
                ref={(el) => {
                  if (el) el.indeterminate = isSomeSelected;
                }}
                onChange={toggleSelectAll}
                className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <label className="text-sm text-gray-700 cursor-pointer" onClick={toggleSelectAll}>
                {isAllSelected ? t('training.deselectAll') : t('training.selectAllOnPage')}
              </label>
            </div>
          )}

          {/* Training states list */}
          <div className="space-y-2 overflow-y-auto flex-1">
            {paginatedStates.map((state) => {
              const isExpanded = expandedId === state.task_id;
              const isSelected = selectedIds.has(state.task_id);
              const isTraining = state.status === 'Training';

              return (
                <div
                  key={state.task_id}
                  className={`border rounded-lg bg-white transition-all ${
                    isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-300'
                  }`}
                >
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      {/* Selection checkbox */}
                      <div className="pt-1">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelection(state.task_id)}
                          className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>

                      {/* Main content */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                              state.status
                            )}`}
                          >
                            {getStatusLabel(state.status)}
                          </span>
                          <span className="text-xs text-gray-500">{state.config.dtype}</span>
                        </div>

                        <p className="text-sm font-medium text-gray-900 mb-1">{state.job_name}</p>

                        <p className="text-xs text-gray-500">
                          {t('training.created')}: {formatDate(state.created_at)}
                        </p>

                        {/* Live metrics display (if training) */}
                        {isTraining && state.current_step !== null && state.current_epoch !== null && (
                          <div className="mt-2 bg-blue-50 rounded p-2 space-y-1">
                            <div className="flex justify-between text-xs">
                              <span>{t('training.currentEpoch')}:</span>
                              <span className="font-semibold">{state.current_epoch} / {state.total_epochs || '?'}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span>{t('training.currentStep')}:</span>
                              <span className="font-semibold">{state.current_step.toLocaleString()}</span>
                            </div>
                            {state.current_loss !== null && (
                              <div className="flex justify-between text-xs">
                                <span>{t('training.currentLoss')}:</span>
                                <span className="font-semibold">{state.current_loss.toFixed(4)}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => toggleDetails(state.task_id)}
                          className="w-32 px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 flex items-center justify-center gap-1"
                        >
                          {isExpanded ? (
                            <>
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                              <span>{t('training.hide')}</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                              <span>{t('training.viewDetails')}</span>
                            </>
                          )}
                        </button>

                        <button
                          onClick={() => handleDeleteClick(state.task_id)}
                          className="w-32 px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 flex items-center justify-center gap-1"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          <span>{t('common.delete')}</span>
                        </button>
                      </div>
                    </div>

                    {/* Expandable Details Section */}
                    {isExpanded && renderStateDetails(state)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between border-t border-gray-300 pt-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700">{t('training.itemsPerPage')}:</label>
                <select
                  value={itemsPerPage}
                  onChange={(e) => handleItemsPerPageChange(Number(e.target.value))}
                  className="border border-gray-300 rounded px-2 py-1 text-sm"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700">
                  {t('training.page')} {currentPage} {t('training.of')} {totalPages} ({t('training.showingItems')
                    .replace('{start}', (startIndex + 1).toString())
                    .replace('{end}', Math.min(endIndex, states.length).toString())
                    .replace('{total}', states.length.toString())})
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => goToPage(1)}
                    disabled={currentPage === 1}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                  >
                    ««
                  </button>
                  <button
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                  >
                    ‹
                  </button>
                  <button
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                  >
                    ›
                  </button>
                  <button
                    onClick={() => goToPage(totalPages)}
                    disabled={currentPage === totalPages}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                  >
                    »»
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">{t('training.confirmDeletionTitle')}</h3>
            <p className="text-gray-600 mb-4">{t('training.confirmDelete')}</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancelDelete}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Export with React.memo to prevent unnecessary re-renders
export default React.memo(TrainingHistory);
