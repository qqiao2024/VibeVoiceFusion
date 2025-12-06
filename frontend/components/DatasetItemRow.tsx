"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import InlineAudioPlayer from "./InlineAudioPlayer";

interface DatasetItemRowProps {
  index: number;
  text: string;
  audioUrl: string;
  audioFilename: string;
  voicePromptUrls: string[];
  voicePromptFilenames: string[];
  onTextUpdate: (newText: string) => Promise<void>;
  onDelete: () => Promise<void>;
}

export default function DatasetItemRow({
  index,
  text,
  audioUrl,
  audioFilename,
  voicePromptUrls,
  voicePromptFilenames,
  onTextUpdate,
  onDelete,
}: DatasetItemRowProps) {
  const { t } = useLanguage();
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(text);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleSave = async () => {
    if (editedText.trim() === text) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      await onTextUpdate(editedText);
      setIsEditing(false);
    } catch (error) {
      console.error("Error updating text:", error);
      // Revert on error
      setEditedText(text);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedText(text);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    try {
      await onDelete();
      setShowDeleteConfirm(false);
    } catch (error) {
      console.error("Error deleting item:", error);
    }
  };

  return (
    <>
      <tr className="border-b border-gray-200 hover:bg-gray-50">
        {/* Index */}
        <td className="px-4 py-3 text-sm text-gray-600 w-16">
          #{index + 1}
        </td>

        {/* Text - Editable */}
        <td className="px-4 py-3">
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                rows={3}
                disabled={isSaving}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                >
                  {isSaving ? t('common.saving') : t('common.save')}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={isSaving}
                  className="px-3 py-1 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <p className="text-sm text-gray-900 flex-1">{text}</p>
              <button
                onClick={() => setIsEditing(true)}
                className="flex-shrink-0 p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title={t('common.edit')}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
            </div>
          )}
        </td>

        {/* Audio File */}
        <td className="px-4 py-3 w-64">
          <InlineAudioPlayer
            audioUrl={audioUrl}
            filename={audioFilename}
          />
        </td>

        {/* Voice Prompts */}
        <td className="px-4 py-3 w-64">
          <div className="space-y-2">
            {voicePromptUrls.map((url, idx) => (
              <InlineAudioPlayer
                key={idx}
                audioUrl={url}
                filename={voicePromptFilenames[idx] || `prompt-${idx + 1}`}
              />
            ))}
          </div>
        </td>

        {/* Actions */}
        <td className="px-4 py-3 w-24">
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title={t('common.delete')}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </td>
      </tr>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <tr>
          <td colSpan={5} className="px-4 py-0">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-2">
              <p className="text-sm text-red-800 mb-3">{t('dataset.deleteItemConfirm')}</p>
              <div className="flex gap-2">
                <button
                  onClick={handleDelete}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
                >
                  {t('common.delete')}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-3 py-1 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
