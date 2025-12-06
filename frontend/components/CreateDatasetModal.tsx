"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n/LanguageContext";

interface CreateDatasetModalProps {
  onClose: () => void;
  onCreate: (name: string, description: string) => void;
}

export default function CreateDatasetModal({ onClose, onCreate }: CreateDatasetModalProps) {
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreate(name.trim(), description.trim());
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">{t('dataset.createDataset')}</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          <div className="space-y-4">
            {/* Name Field */}
            <div>
              <label htmlFor="dataset-name" className="block text-sm font-medium text-gray-700 mb-1">
                {t('dataset.datasetName')} <span className="text-red-500">*</span>
              </label>
              <input
                id="dataset-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('dataset.namePlaceholder')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                autoFocus
              />
            </div>

            {/* Description Field */}
            <div>
              <label htmlFor="dataset-description" className="block text-sm font-medium text-gray-700 mb-1">
                {t('dataset.description')}
              </label>
              <textarea
                id="dataset-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('dataset.descriptionPlaceholder')}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end space-x-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-blue-400 disabled:cursor-not-allowed"
              disabled={isSubmitting || !name.trim()}
            >
              {isSubmitting ? t('common.saving') : t('common.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
