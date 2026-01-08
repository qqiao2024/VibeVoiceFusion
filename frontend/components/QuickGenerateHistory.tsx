'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import { api } from '@/lib/api';
import type { QuickGenerate, QuickGenerateHistoryItem, QuickGenerateItem } from '@/types/quickGenerate';
import toast from 'react-hot-toast';

interface QuickGenerateHistoryProps {
  onSelectGeneration: (generation: QuickGenerate) => void;
  currentGenerationId?: string;
  currentGenerationStatus?: string;
}

export default function QuickGenerateHistory({ onSelectGeneration, currentGenerationId, currentGenerationStatus }: QuickGenerateHistoryProps) {
  const { t } = useLanguage();
  const [generations, setGenerations] = useState<QuickGenerateHistoryItem[]>([]);
  const [expandedGeneration, setExpandedGeneration] = useState<QuickGenerate | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [total, setTotal] = useState(0);

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<'single' | 'bulk'>('single');
  const [singleDeleteId, setSingleDeleteId] = useState<string | null>(null);

  // Load history
  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const offset = (currentPage - 1) * itemsPerPage;
      const response = await api.listQuickGenerationHistory({ offset, limit: itemsPerPage });
      setGenerations(response.generations);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load quick generation history:', err);
      toast.error(t('quickGenerate.errorLoadHistory'));
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, t]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Refresh when current generation changes or completes
  useEffect(() => {
    if (currentGenerationId) {
      loadHistory();
    }
  }, [currentGenerationId, loadHistory]);

  // Refresh history when generation status changes to completed or failed
  useEffect(() => {
    if (currentGenerationStatus === 'completed' || currentGenerationStatus === 'failed') {
      loadHistory();
    }
  }, [currentGenerationStatus, loadHistory]);

  const totalPages = Math.ceil(total / itemsPerPage);

  const toggleDetails = useCallback(async (requestId: string) => {
    if (expandedId === requestId) {
      setExpandedId(null);
      setExpandedGeneration(null);
    } else {
      setExpandedId(requestId);
      // Fetch full generation data for expanded view
      try {
        const fullGen = await api.getQuickGeneration(requestId);
        setExpandedGeneration(fullGen);
      } catch (err) {
        console.error('Failed to load generation details:', err);
        setExpandedGeneration(null);
      }
    }
  }, [expandedId]);

  // Selection handlers
  const toggleSelection = useCallback((requestId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds(prev => {
      const newSelected = new Set(prev);
      if (newSelected.has(requestId)) {
        newSelected.delete(requestId);
      } else {
        newSelected.add(requestId);
      }
      return newSelected;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds(prev => {
      if (prev.size === generations.length) {
        return new Set();
      } else {
        return new Set(generations.map(g => g.request_id));
      }
    });
  }, [generations]);

  const isAllSelected = generations.length > 0 && selectedIds.size === generations.length;

  // Delete handlers
  const handleDeleteClick = useCallback((requestId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSingleDeleteId(requestId);
    setDeleteTarget('single');
    setShowDeleteDialog(true);
  }, []);

  const handleBulkDeleteClick = useCallback(() => {
    if (selectedIds.size === 0) return;
    setDeleteTarget('bulk');
    setShowDeleteDialog(true);
  }, [selectedIds.size]);

  const handleConfirmDelete = useCallback(async () => {
    try {
      if (deleteTarget === 'single' && singleDeleteId) {
        await api.deleteQuickGeneration(singleDeleteId);
        toast.success(t('quickGenerate.deleted'));
      } else if (deleteTarget === 'bulk') {
        await Promise.all(Array.from(selectedIds).map(id => api.deleteQuickGeneration(id)));
        toast.success(t('quickGenerate.bulkDeleted').replace('{count}', String(selectedIds.size)));
        setSelectedIds(new Set());
      }
      setShowDeleteDialog(false);
      setSingleDeleteId(null);
      loadHistory();
    } catch (err) {
      console.error('Failed to delete generation(s):', err);
      toast.error(t('quickGenerate.errorDelete'));
    }
  }, [deleteTarget, singleDeleteId, selectedIds, t, loadHistory]);

  const handleCancelDelete = useCallback(() => {
    setShowDeleteDialog(false);
    setSingleDeleteId(null);
  }, []);

  const handleSelectGeneration = useCallback(async (gen: QuickGenerateHistoryItem) => {
    try {
      const fullGen = await api.getQuickGeneration(gen.request_id);
      onSelectGeneration(fullGen);
    } catch (err) {
      console.error('Failed to load generation:', err);
      toast.error(t('quickGenerate.errorLoadHistory'));
    }
  }, [onSelectGeneration, t]);

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { bg: string; text: string }> = {
      completed: { bg: 'bg-green-100', text: 'text-green-800' },
      failed: { bg: 'bg-red-100', text: 'text-red-800' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
      preprocessing: { bg: 'bg-blue-100', text: 'text-blue-800' },
      inferencing: { bg: 'bg-blue-100', text: 'text-blue-800' },
    };
    const config = statusConfig[status] || { bg: 'bg-gray-100', text: 'text-gray-800' };
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.bg} ${config.text}`}>
        {t(`quickGenerate.status.${status}`) || status}
      </span>
    );
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  if (loading && generations.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{t('quickGenerate.history')}</h2>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <button
              onClick={handleBulkDeleteClick}
              className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 flex items-center gap-1.5 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              {t('quickGenerate.deleteSelected')} ({selectedIds.size})
            </button>
          )}
          <button
            onClick={() => loadHistory()}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title={t('common.refresh')}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Empty State */}
      {generations.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
          <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <p className="text-sm">{t('quickGenerate.noHistory')}</p>
        </div>
      ) : (
        <>
          {/* Select All */}
          <div className="flex items-center gap-2 px-2 py-1 mb-2">
            <input
              type="checkbox"
              checked={isAllSelected}
              onChange={toggleSelectAll}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-500">{t('common.selectAll')}</span>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto space-y-2">
            {generations.map((gen) => (
              <div
                key={gen.request_id}
                className={`border rounded-lg transition-all cursor-pointer ${
                  currentGenerationId === gen.request_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
                onClick={() => handleSelectGeneration(gen)}
              >
                {/* Main Info */}
                <div className="p-3">
                  <div className="flex items-start gap-2">
                    {/* Checkbox */}
                    <input
                      type="checkbox"
                      checked={selectedIds.has(gen.request_id)}
                      onChange={() => {}}
                      onClick={(e) => toggleSelection(gen.request_id, e)}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(gen.status)}
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          gen.detected_mode === 'dialogue'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {gen.detected_mode === 'dialogue'
                            ? t('quickGenerate.dialogueMode')
                            : t('quickGenerate.narrationMode')}
                        </span>
                        {gen.batch_size > 1 && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-orange-100 text-orange-800">
                            x{gen.batch_size}
                          </span>
                        )}
                      </div>

                      {/* Text Preview */}
                      <p className="text-sm text-gray-700 truncate mb-1">
                        {gen.text_preview || '...'}
                      </p>

                      {/* Date */}
                      <p className="text-xs text-gray-500">
                        {formatDate(gen.created_at)}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleDetails(gen.request_id);
                        }}
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                      >
                        <svg className={`w-4 h-4 transition-transform ${expandedId === gen.request_id ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => handleDeleteClick(gen.request_id, e)}
                        className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 flex items-center gap-1 transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        {t('common.delete')}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === gen.request_id && expandedGeneration && (
                  <div className="px-3 pb-3 pt-2 border-t border-gray-100 space-y-3">
                    {/* Voice Preview */}
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        {t('quickGenerate.voicePrompt')}
                        {expandedGeneration.voice_files && expandedGeneration.voice_files.length > 1 && (
                          <span className="ml-1 text-gray-400">({expandedGeneration.voice_files.length})</span>
                        )}
                      </p>
                      {expandedGeneration.voice_files && expandedGeneration.voice_files.length > 1 ? (
                        <div className="space-y-2">
                          {expandedGeneration.voice_files.map((_: string, idx: number) => (
                            <div key={idx} className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 w-6">#{idx + 1}</span>
                              <audio
                                controls
                                className="flex-1 h-8"
                                src={api.getQuickGenerationVoicePreviewByIndexUrl(gen.request_id, idx)}
                              />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <audio
                          controls
                          className="w-full h-8"
                          src={api.getQuickGenerationVoicePreviewUrl(gen.request_id)}
                        />
                      )}
                    </div>

                    {/* Full Text */}
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">{t('quickGenerate.fullText')}</p>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-2 rounded max-h-32 overflow-y-auto">
                        {expandedGeneration.text}
                      </p>
                    </div>

                    {/* Generated Audio (if completed) */}
                    {gen.status === 'completed' && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-1">{t('quickGenerate.generatedAudio')}</p>
                        {gen.batch_size > 1 && expandedGeneration.details?.generation_items ? (
                          <div className="space-y-2">
                            {expandedGeneration.details.generation_items.map((item: QuickGenerateItem, idx: number) => (
                              <div key={idx} className="flex items-center gap-2">
                                <span className="text-xs text-gray-500 w-6">#{idx + 1}</span>
                                <audio
                                  controls
                                  className="flex-1 h-8"
                                  src={api.getQuickGenerationItemDownloadUrl(gen.request_id, idx)}
                                />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <audio
                            controls
                            className="w-full h-8"
                            src={api.getQuickGenerationDownloadUrl(gen.request_id)}
                          />
                        )}
                      </div>
                    )}

                    {/* Seed Info */}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{t('quickGenerate.seed')}: {expandedGeneration.seeds}</span>
                      <span>{t('quickGenerate.cfgScale')}: {expandedGeneration.cfg_scale}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 mt-4">
              <p className="text-sm text-gray-500">
                {t('common.showingOf')
                  .replace('{start}', String((currentPage - 1) * itemsPerPage + 1))
                  .replace('{end}', String(Math.min(currentPage * itemsPerPage, total)))
                  .replace('{total}', String(total))}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('common.previous')}
                </button>
                <span className="text-sm text-gray-600">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('common.next')}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-2">{t('quickGenerate.confirmDeletionTitle')}</h3>
            <p className="text-gray-600 mb-4">
              {deleteTarget === 'single'
                ? t('quickGenerate.confirmSingleDelete')
                : t('quickGenerate.confirmBulkDelete')
                    .replace('{count}', selectedIds.size.toString())
                    .replace('{plural}', selectedIds.size > 1 ? 's' : '')}
            </p>
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
