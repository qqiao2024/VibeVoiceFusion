"use client";

import { useState, useRef } from "react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import InlineAudioPlayer from "./InlineAudioPlayer";

interface DatasetItemModalProps {
  onClose: () => void;
  onSave: (text: string, audioFile: File, voicePromptFiles: File[]) => Promise<void>;
  initialText?: string;
  mode: "create" | "edit";
}

export default function DatasetItemModal({ onClose, onSave, initialText = "", mode }: DatasetItemModalProps) {
  const { t } = useLanguage();
  const [text, setText] = useState(initialText);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [voicePromptFiles, setVoicePromptFiles] = useState<File[]>([]);
  const [voicePromptPreviewUrls, setVoicePromptPreviewUrls] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const audioInputRef = useRef<HTMLInputElement>(null);
  const voicePromptsInputRef = useRef<HTMLInputElement>(null);

  const handleAudioUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      // Create preview URL
      const url = URL.createObjectURL(file);
      setAudioPreviewUrl(url);
    }
  };

  const handleVoicePromptsUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setVoicePromptFiles([...voicePromptFiles, ...files]);
      // Create preview URLs
      const urls = files.map(file => URL.createObjectURL(file));
      setVoicePromptPreviewUrls([...voicePromptPreviewUrls, ...urls]);
    }
  };

  const removeAudioFile = () => {
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
    }
    setAudioFile(null);
    setAudioPreviewUrl(null);
    if (audioInputRef.current) {
      audioInputRef.current.value = "";
    }
  };

  const removeVoicePrompt = (index: number) => {
    const url = voicePromptPreviewUrls[index];
    if (url) {
      URL.revokeObjectURL(url);
    }
    setVoicePromptFiles(voicePromptFiles.filter((_, i) => i !== index));
    setVoicePromptPreviewUrls(voicePromptPreviewUrls.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!text.trim()) {
      alert(t('dataset.textRequired'));
      return;
    }

    if (!audioFile && mode === "create") {
      alert(t('dataset.audioRequired'));
      return;
    }

    if (voicePromptFiles.length === 0 && mode === "create") {
      alert(t('dataset.voicePromptsRequired'));
      return;
    }

    setSaving(true);
    try {
      await onSave(text, audioFile!, voicePromptFiles);
      // Cleanup URLs
      if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
      voicePromptPreviewUrls.forEach(url => URL.revokeObjectURL(url));
      onClose();
    } catch (error) {
      console.error("Error saving item:", error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {mode === "create" ? t('dataset.createItem') : t('dataset.editItem')}
          </h2>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Text Field */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('dataset.text')} <span className="text-red-500">*</span>
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={t('dataset.textPlaceholder')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={4}
            />
          </div>

          {/* Audio File */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('dataset.audioFile')} {mode === "create" && <span className="text-red-500">*</span>}
            </label>

            {audioPreviewUrl ? (
              <div className="space-y-2">
                <InlineAudioPlayer
                  audioUrl={audioPreviewUrl}
                  filename={audioFile?.name || "audio"}
                />
                <button
                  onClick={removeAudioFile}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  {t('common.remove')}
                </button>
              </div>
            ) : (
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <input
                  ref={audioInputRef}
                  type="file"
                  accept="audio/*"
                  onChange={handleAudioUpload}
                  className="hidden"
                />
                <button
                  onClick={() => audioInputRef.current?.click()}
                  className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {t('dataset.uploadAudio')}
                </button>
                <p className="text-sm text-gray-500 mt-2">{t('dataset.supportedAudioFormats')}</p>
              </div>
            )}
          </div>

          {/* Voice Prompts */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('dataset.voicePrompts')} {mode === "create" && <span className="text-red-500">*</span>}
            </label>

            {voicePromptPreviewUrls.length > 0 && (
              <div className="space-y-2 mb-4">
                {voicePromptPreviewUrls.map((url, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <div className="flex-1">
                      <InlineAudioPlayer
                        audioUrl={url}
                        filename={voicePromptFiles[index]?.name || `voice-prompt-${index + 1}`}
                      />
                    </div>
                    <button
                      onClick={() => removeVoicePrompt(index)}
                      className="flex-shrink-0 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <input
                ref={voicePromptsInputRef}
                type="file"
                accept="audio/*"
                multiple
                onChange={handleVoicePromptsUpload}
                className="hidden"
              />
              <button
                onClick={() => voicePromptsInputRef.current?.click()}
                className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                {t('dataset.addVoicePrompt')}
              </button>
              <p className="text-sm text-gray-500 mt-2">{t('dataset.multipleFilesAllowed')}</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving && (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {t('common.save')}
          </button>
        </div>
      </div>
    </div>
  );
}
