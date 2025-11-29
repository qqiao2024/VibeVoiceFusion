"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useProject } from "@/lib/ProjectContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { DatasetItem } from "@/lib/api";
import DatasetItemRow from "@/components/DatasetItemRow";
import DatasetItemModal from "@/components/DatasetItemModal";
import toast from "react-hot-toast";

// Mock data for UI testing
const MOCK_ITEMS: DatasetItem[] = Array.from({ length: 20 }, (_, i) => ({
  text: `This is sample text for dataset item ${i + 1}. It demonstrates how the text will be displayed in the table row with inline editing capabilities.`,
  audio: `audio_${i + 1}.wav`,
  voice_prompts: [`prompt_${i + 1}_1.wav`, `prompt_${i + 1}_2.wav`, `prompt_${i + 1}_3.wav`],
}));

export default function DatasetDetailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const datasetId = searchParams.get('id');
  const { currentProject, loading } = useProject();
  const { t } = useLanguage();

  // Use mock data instead of API
  const [items, setItems] = useState<DatasetItem[]>(MOCK_ITEMS);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [dataset] = useState({
    id: datasetId || '',
    name: "Sample Dataset",
    description: "This is a mock dataset for UI testing",
    item_count: MOCK_ITEMS.length,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Virtual scrolling state
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Redirect if no dataset ID or no project
  useEffect(() => {
    if (!loading && !currentProject) {
      router.push('/');
    } else if (!datasetId) {
      router.push('/dataset');
    }
  }, [loading, currentProject, datasetId, router]);

  // Handle scroll for virtual scrolling
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const scrollTop = target.scrollTop;
    const itemHeight = 150; // Approximate row height
    const containerHeight = target.clientHeight;

    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - 5);
    const end = Math.min(items.length, Math.ceil((scrollTop + containerHeight) / itemHeight) + 5);

    setVisibleRange({ start, end });
  };

  const handleCreateItem = async (text: string, audioFile: File, voicePromptFiles: File[]) => {
    // Mock create - just add to the list
    const newItem: DatasetItem = {
      text,
      audio: audioFile.name,
      voice_prompts: voicePromptFiles.map(f => f.name),
    };
    setItems([...items, newItem]);
    setShowCreateModal(false);
    toast.success(t('dataset.itemCreated'));
  };

  const handleTextUpdate = async (index: number, newText: string) => {
    // Mock update - just update the array
    const updatedItems = [...items];
    updatedItems[index] = { ...updatedItems[index], text: newText };
    setItems(updatedItems);
    toast.success(t('dataset.itemUpdated'));
  };

  const handleDelete = async (index: number) => {
    // Mock delete - just remove from array
    setItems(items.filter((_, i) => i !== index));
    toast.success(t('dataset.itemDeleted'));
  };

  const handleBack = () => {
    router.push('/dataset');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Build mock audio URLs for items
  const getAudioUrls = () => {
    return items.map(item => ({
      // Use placeholder URLs for mock data
      audioUrl: `#mock-audio-${item.audio}`,
      voicePromptUrls: item.voice_prompts.map(vp => `#mock-prompt-${vp}`),
    }));
  };

  const audioUrls = getAudioUrls();

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
                {datasetLoading ? t('common.loading') : dataset?.name}
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
              <span>{items.length} {t('dataset.totalItems')}</span>
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
        {datasetLoading ? (
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
                    const urls = audioUrls[actualIndex];

                    return (
                      <DatasetItemRow
                        key={actualIndex}
                        index={actualIndex}
                        text={item.text}
                        audioUrl={urls.audioUrl}
                        audioFilename={item.audio}
                        voicePromptUrls={urls.voicePromptUrls}
                        voicePromptFilenames={item.voice_prompts}
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
