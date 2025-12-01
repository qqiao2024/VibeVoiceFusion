'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useProject } from '@/lib/ProjectContext';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import { TrainingProvider, useTraining } from '@/lib/TrainingContext';
import { DatasetProvider } from '@/lib/DatasetContext';
import TrainingHistory from '@/components/TrainingHistory';
import CurrentTraining from '@/components/CurrentTraining';
import TrainingForm from '@/components/TrainingForm';

function TrainingContent() {
  const { currentProject } = useProject();
  const { currentJob } = useTraining();
  const { t } = useLanguage();

  // Safety check - should not happen due to wrapper logic, but prevents errors
  if (!currentProject) {
    return null;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center space-x-2 mb-1">
          <h1 className="text-2xl font-bold text-gray-900">{t('training.pageTitle')}</h1>
          {currentProject && (
            <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
              {currentProject.name}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500">
          {t('training.pageSubtitle')}
        </p>
      </header>

      {/* Main Content - Two Column Layout */}
      <div className="flex-1 overflow-hidden bg-gray-50">
        <div className="h-full grid grid-cols-2 gap-6 p-6">
          {/* Left Column - Training History */}
          <div className="bg-white rounded-lg shadow-sm p-6 overflow-hidden flex flex-col">
            <TrainingHistory />
          </div>

          {/* Right Column - Current Training or Form */}
          <div className="flex flex-col gap-6 overflow-y-auto">
            {/* Current Training Status (if active) */}
            {currentJob && <CurrentTraining />}

            {/* Training Form (if no active training) */}
            {!currentJob && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <TrainingForm />
              </div>
            )}

            {/* Info Card */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">{t('training.howItWorks')}</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>{t('training.step1')}</li>
                <li>{t('training.step2')}</li>
                <li>{t('training.step3')}</li>
                <li>{t('training.step4')}</li>
                <li>{t('training.step5')}</li>
              </ul>
            </div>

            {/* Technical Info */}
            <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">{t('training.technicalInfo')}</h3>
              <div className="text-xs text-gray-700 space-y-1">
                <p><strong>LoRA:</strong> {t('training.loraInfo')}</p>
                <p><strong>AdamW8bit:</strong> {t('training.adamw8bitInfo')}</p>
                <p><strong>Gradient Accumulation:</strong> {t('training.gradientAccumulationInfo')}</p>
                <p><strong>Layer Offloading:</strong> {t('training.layerOffloadingInfo')}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function TrainingPage() {
  const router = useRouter();
  const { currentProject, loading } = useProject();
  const { t } = useLanguage();

  // Redirect to home page if no project is selected (after loading completes)
  useEffect(() => {
    if (!loading && !currentProject) {
      router.push('/');
    }
  }, [loading, currentProject, router]);

  // Show content when project is available
  const showContent = !loading && currentProject;

  return (
    <div className="h-full flex flex-col">
      {showContent ? (
        <DatasetProvider projectId={currentProject.id}>
          <TrainingProvider projectId={currentProject.id}>
            <TrainingContent />
          </TrainingProvider>
        </DatasetProvider>
      ) : (
        <>
          <header className="bg-white border-b border-gray-200 px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-900">{t('training.pageTitle')}</h1>
            <p className="text-sm text-gray-500 mt-1">{t('training.pageSubtitle')}</p>
          </header>

          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-500">
                {loading ? t('training.loadingProject') : t('training.redirecting')}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
