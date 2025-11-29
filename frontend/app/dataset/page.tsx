"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useProject } from "@/lib/ProjectContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import DatasetCard from "@/components/DatasetCard";
import CreateDatasetModal from "@/components/CreateDatasetModal";

interface Dataset {
  id: string;
  name: string;
  description: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export default function DatasetPage() {
  const router = useRouter();
  const { currentProject, loading } = useProject();
  const { t } = useLanguage();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loadingDatasets, setLoadingDatasets] = useState(true);

  // Redirect to home page if no project is selected (after loading completes)
  useEffect(() => {
    if (!loading && !currentProject) {
      router.push('/');
    }
  }, [loading, currentProject, router]);

  // Fetch datasets when project is available
  useEffect(() => {
    if (currentProject) {
      fetchDatasets();
    }
  }, [currentProject]);

  const fetchDatasets = async () => {
    if (!currentProject) return;

    setLoadingDatasets(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/projects/${currentProject.id}/datasets`);
      // const data = await response.json();
      // setDatasets(data);

      // Mock data for now
      setDatasets([
        {
          id: "1",
          name: "Training Dataset 1",
          description: "Voice samples for speaker adaptation",
          item_count: 150,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: "2",
          name: "Validation Dataset",
          description: "Test samples for model evaluation",
          item_count: 50,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error("Error fetching datasets:", error);
    } finally {
      setLoadingDatasets(false);
    }
  };

  const handleCreateDataset = async (name: string, description: string) => {
    if (!currentProject) return;

    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/projects/${currentProject.id}/datasets`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ name, description })
      // });
      // const newDataset = await response.json();

      // Mock for now
      const newDataset: Dataset = {
        id: String(Date.now()),
        name,
        description,
        item_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      setDatasets([...datasets, newDataset]);
      setShowCreateModal(false);
    } catch (error) {
      console.error("Error creating dataset:", error);
    }
  };

  const handleDeleteDataset = async (id: string) => {
    if (!currentProject) return;

    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/projects/${currentProject.id}/datasets/${id}`, {
      //   method: 'DELETE'
      // });

      setDatasets(datasets.filter(d => d.id !== id));
    } catch (error) {
      console.error("Error deleting dataset:", error);
    }
  };

  const handleViewDetails = (id: string) => {
    router.push(`/dataset/${id}`);
  };

  // Show content when project is available
  const showContent = !loading && currentProject;

  return (
    <div className="h-full flex flex-col">
      {showContent ? (
        <>
          {/* Header */}
          <header className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center space-x-2 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">{t('dataset.title')}</h1>
              {currentProject && (
                <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                  {currentProject.name}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {t('dataset.title')}
            </p>
          </header>

          {/* Content */}
          <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
            {/* Action Bar */}
            <div className="flex items-center justify-between mb-6">
              <p className="text-sm text-gray-600">
                {t('dataset.title')}
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>{t('dataset.createDataset')}</span>
              </button>
            </div>
            {/* Dataset Grid */}
            {loadingDatasets ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">{t('common.loading')}</div>
              </div>
            ) : datasets.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64">
                <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
                <p className="text-gray-500 text-center">{t('dataset.noDatasets')}</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  {t('dataset.createDataset')}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {datasets.map((dataset) => (
                  <DatasetCard
                    key={dataset.id}
                    dataset={dataset}
                    onDelete={handleDeleteDataset}
                    onViewDetails={handleViewDetails}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Create Dataset Modal */}
          {showCreateModal && (
            <CreateDatasetModal
              onClose={() => setShowCreateModal(false)}
              onCreate={handleCreateDataset}
            />
          )}
        </>
      ) : null}
    </div>
  );
}
