"use client";

import { useEffect, useState, useRef, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useProject } from "@/lib/ProjectContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { DatasetItemsProvider, useDatasetItems } from "@/lib/DatasetItemsContext";
import { api, Dataset } from "@/lib/api";
import DatasetItemRow from "@/components/DatasetItemRow";
import DatasetItemModal from "@/components/DatasetItemModal";
import toast from "react-hot-toast";

// Main content component that uses contexts
function DatasetDetailContent({ datasetId }: { datasetId: string }) {
  const router = useRouter();
  const { currentProject } = useProject();
  const { t } = useLanguage();
  const { items, totalCount, loading, createItem, updateItem, deleteItem } = useDatasetItems();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [datasetLoading, setDatasetLoading] = useState(true);

  // Virtual scrolling state
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Load dataset metadata
  const loadDataset = useCallback(async () => {
    if (!currentProject || !datasetId) return;

    setDatasetLoading(true);
    try {
      const data = await api.getDataset(currentProject.id, datasetId);
      setDataset(data);
    } catch (err) {
      console.error("Failed to load dataset:", err);
      toast.error("Failed to load dataset");
    } finally {
      setDatasetLoading(false);
    }
  }, [currentProject, datasetId]);

  useEffect(() => {
    loadDataset();
  }, [loadDataset]);

  // Handle scroll for virtual scrolling
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const scrollTop = target.scrollTop;
    const itemHeight = 150; // Approximate row height
    const containerHeight = target.clientHeight;

    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - 5);
    const end = Math.min(totalCount, Math.ceil((scrollTop + containerHeight) / itemHeight) + 5);

    setVisibleRange({ start, end });
  };

  const handleCreateItem = async (text: string, audioFile: File, voicePromptFiles: File[]) => {
    try {
      await createItem(text, audioFile, voicePromptFiles);
      setShowCreateModal(false);
      toast.success(t('dataset.itemCreated'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create item');
    }
  };

  const handleTextUpdate = async (index: number, newText: string) => {
    try {
      await updateItem(index, newText);
      toast.success(t('dataset.itemUpdated'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update item');
    }
  };

  const handleDelete = async (index: number) => {
    try {
      await deleteItem(index);
      toast.success(t('dataset.itemDeleted'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete item');
    }
  };

  const handleBack = () => {
    router.push('/dataset');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Helper to extract filename from relative path
  const extractFilename = (path: string) => {
    // Extract filename from relative path (e.g., "./audio/file.wav" -> "file.wav")
    return path.split('/').pop() || path;
  };

  // Get audio URLs for an item
  const getAudioUrl = (path: string) => {
    if (!currentProject || !datasetId) return '';
    const filename = extractFilename(path);
    // The audio files are stored in workspace/{project_id}/datasets/{dataset_id}/audio/{filename}
    // We'll need to add a backend endpoint to serve these files, or use a direct path
    // For now, returning a placeholder that should work when backend serves files
    return `/api/v1/projects/${currentProject.id}/datasets/${datasetId}/audio/${filename}`;
  };

  const getVoicePromptUrl = (path: string) => {
    if (!currentProject || !datasetId) return '';
    const filename = extractFilename(path);
    return `/api/v1/projects/${currentProject.id}/datasets/${datasetId}/voice-prompts/${filename}`;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center space-x-4 mb-2">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">
                {datasetLoading ? t('common.loading') : (dataset?.name || 'Dataset')}
              </h1>
              {currentProject && (
                <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                  {currentProject.name}
                </span>
              )}
            </div>
            {dataset?.description && (
              <p className="text-sm text-gray-600">{dataset.description}</p>
            )}
          </div>
        </div>

        {dataset && (
          <div className="flex items-center space-x-6 text-sm text-gray-500">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>{totalCount} {t('dataset.totalItems')}</span>
            </div>
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{t('dataset.updatedAt')}: {formatDate(dataset.updated_at)}</span>
            </div>
          </div>
        )}
      </header>

      {/* Action Bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{t('dataset.itemManagement')}</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>{t('dataset.createItem')}</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-gray-50"
        onScroll={handleScroll}
      >
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-500 text-center mb-4">{t('dataset.noItems')}</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              {t('dataset.createItem')}
            </button>
          </div>
        ) : (
          <div className="p-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                      #
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('dataset.text')}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-64">
                      {t('dataset.audioFile')}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-64">
                      {t('dataset.voicePrompts')}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                      {t('dataset.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {/* Virtual scrolling: only render visible items */}
                  {items.slice(visibleRange.start, visibleRange.end).map((item, idx) => {
                    const actualIndex = visibleRange.start + idx;

                    // Only render if item exists (handle sparse array from pagination)
                    if (!item) return null;

                    return (
                      <DatasetItemRow
                        key={actualIndex}
                        index={actualIndex}
                        text={item.text}
                        audioUrl={getAudioUrl(item.audio)}
                        audioFilename={extractFilename(item.audio)}
                        voicePromptUrls={item.voice_prompts.map(getVoicePromptUrl)}
                        voicePromptFilenames={item.voice_prompts.map(extractFilename)}
                        onTextUpdate={(newText) => handleTextUpdate(actualIndex, newText)}
                        onDelete={() => handleDelete(actualIndex)}
                      />
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Create Item Modal */}
      {showCreateModal && (
        <DatasetItemModal
          mode="create"
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreateItem}
        />
      )}
    </div>
  );
}

// Inner component that uses useSearchParams
function DatasetDetailPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const datasetId = searchParams.get('id');
  const { currentProject, loading } = useProject();
  const { t } = useLanguage();

  // Redirect if no dataset ID or no project
  useEffect(() => {
    if (!loading && !currentProject) {
      router.push('/');
    } else if (!datasetId) {
      router.push('/dataset');
    }
  }, [loading, currentProject, datasetId, router]);

  // Show loading state
  if (loading || !currentProject || !datasetId) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Dataset Items</h1>
        </header>
        <div className="flex-1 flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-500">{loading ? t('common.loading') : 'Redirecting...'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <DatasetItemsProvider projectId={currentProject.id} datasetId={datasetId}>
      <DatasetDetailContent datasetId={datasetId} />
    </DatasetItemsProvider>
  );
}

// Page component with Suspense boundary
export default function DatasetDetailPage() {
  return (
    <Suspense fallback={
      <div className="h-full flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Dataset Items</h1>
        </header>
        <div className="flex-1 flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-500">Loading...</p>
          </div>
        </div>
      </div>
    }>
      <DatasetDetailPageContent />
    </Suspense>
  );
}
