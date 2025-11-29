"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useProject } from "@/lib/ProjectContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { DatasetProvider, useDataset } from "@/lib/DatasetContext";
import DatasetCard from "@/components/DatasetCard";
import CreateDatasetModal from "@/components/CreateDatasetModal";
import toast from "react-hot-toast";

function DatasetPageContent() {
  const router = useRouter();
  const { currentProject, loading } = useProject();
  const { t } = useLanguage();
  const { datasets, loading: loadingDatasets, createDataset, deleteDataset } = useDataset();
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Redirect to home page if no project is selected (after loading completes)
  useEffect(() => {
    if (!loading && !currentProject) {
      router.push('/');
    }
  }, [loading, currentProject, router]);

  const handleCreateDataset = async (name: string, description: string) => {
    try {
      await createDataset(name, description);
      setShowCreateModal(false);
      toast.success(t('dataset.createSuccess'));
    } catch (error) {
      console.error("Error creating dataset:", error);
      toast.error(error instanceof Error ? error.message : t('dataset.createError'));
    }
  };

  const handleDeleteDataset = async (id: string) => {
    try {
      await deleteDataset(id);
      toast.success(t('dataset.deleteSuccess'));
    } catch (error) {
      console.error("Error deleting dataset:", error);
      toast.error(error instanceof Error ? error.message : t('dataset.deleteError'));
    }
  };

  const handleViewDetails = (id: string) => {
    router.push(`/dataset/detail?id=${id}`);
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
              {t('dataset.description')}
            </p>
          </header>

          {/* Content */}
          <div className="flex-1 overflow-y-auto bg-gray-50">
            {/* Action Bar */}
            <div className="border-b border-gray-200 bg-white px-6 py-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  {t('dataset.manageDatasets')}
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
            </div>

            {/* Dataset Grid */}
            <div className="p-6">
            {loadingDatasets ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
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

export default function DatasetPage() {
  const { currentProject, loading } = useProject();

  // Show content when project is available
  const showContent = !loading && currentProject;

  return showContent ? (
    <DatasetProvider projectId={currentProject!.id}>
      <DatasetPageContent />
    </DatasetProvider>
  ) : (
    <div className="h-full flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Dataset Management</h1>
      </header>
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">{loading ? 'Loading...' : 'Select a project'}</p>
        </div>
      </div>
    </div>
  );
}
