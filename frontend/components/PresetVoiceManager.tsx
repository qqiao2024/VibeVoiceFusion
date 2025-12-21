"use client";

import { useState, useEffect, useRef } from "react";
import { usePresetVoice, PresetVoiceProvider } from "@/lib/PresetVoiceContext";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { api } from "@/lib/api";
import type { PresetVoice } from "@/types/preset";
import toast from "react-hot-toast";

interface PresetVoiceManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

function PresetVoiceManagerContent({ onClose }: { onClose: () => void }) {
  const { t } = useLanguage();
  const {
    presets,
    total,
    loading,
    languages,
    offset,
    limit,
    languageFilter,
    genderFilter,
    hasBgmFilter,
    loadPresets,
    loadLanguages,
    setPage,
    setLimit,
    setLanguageFilter,
    setGenderFilter,
    setHasBgmFilter,
    createPreset,
    deletePreset,
    batchDeletePresets,
  } = usePresetVoice();

  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedFilenames, setSelectedFilenames] = useState<Set<string>>(new Set());
  const [playingFilename, setPlayingFilename] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Add form state
  const [newName, setNewName] = useState("");
  const [newLanguage, setNewLanguage] = useState("en");
  const [newGender, setNewGender] = useState<"man" | "woman">("woman");
  const [newHasBgm, setNewHasBgm] = useState(false);
  const [newVoiceFile, setNewVoiceFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load data on mount
  useEffect(() => {
    loadPresets();
    loadLanguages();
  }, [loadPresets, loadLanguages]);

  const currentPage = Math.floor(offset / limit);
  const totalPages = Math.ceil(total / limit);

  const handleSelectAll = () => {
    if (selectedFilenames.size === presets.length) {
      setSelectedFilenames(new Set());
    } else {
      setSelectedFilenames(new Set(presets.map(p => p.filename)));
    }
  };

  const handleSelectOne = (filename: string) => {
    const newSet = new Set(selectedFilenames);
    if (newSet.has(filename)) {
      newSet.delete(filename);
    } else {
      newSet.add(filename);
    }
    setSelectedFilenames(newSet);
  };

  const handleDelete = async (preset: PresetVoice) => {
    if (!confirm(t('presetVoice.deleteConfirm'))) return;

    const success = await deletePreset(preset.filename);
    if (success) {
      toast.success(t('presetVoice.deleteSuccess'));
      setSelectedFilenames(prev => {
        const newSet = new Set(prev);
        newSet.delete(preset.filename);
        return newSet;
      });
    } else {
      toast.error(t('presetVoice.deleteError'));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedFilenames.size === 0) return;
    if (!confirm(t('presetVoice.batchDeleteConfirm').replace('{count}', String(selectedFilenames.size)))) return;

    try {
      const result = await batchDeletePresets(Array.from(selectedFilenames));
      if (result.deleted.length > 0) {
        toast.success(t('presetVoice.batchDeleteSuccess').replace('{count}', String(result.deleted.length)));
      }
      if (result.failed.length > 0) {
        toast.error(t('presetVoice.batchDeletePartialError').replace('{count}', String(result.failed.length)));
      }
      setSelectedFilenames(new Set());
    } catch {
      toast.error(t('presetVoice.deleteError'));
    }
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newVoiceFile) return;

    setIsSubmitting(true);
    try {
      await createPreset({
        name: newName.trim(),
        language: newLanguage,
        gender: newGender,
        has_bgm: newHasBgm,
        voice_file: newVoiceFile,
      });
      toast.success(t('presetVoice.createSuccess'));
      setShowAddForm(false);
      setNewName("");
      setNewLanguage("en");
      setNewGender("woman");
      setNewHasBgm(false);
      setNewVoiceFile(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('presetVoice.createError'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePlayPreview = (preset: PresetVoice) => {
    if (playingFilename === preset.filename) {
      // Stop playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingFilename(null);
    } else {
      // Stop current if playing
      if (audioRef.current) {
        audioRef.current.pause();
      }
      // Play new
      const audio = new Audio(api.getPresetPreviewUrl(preset.filename));
      audio.onended = () => setPlayingFilename(null);
      audio.onerror = () => {
        toast.error(t('presetVoice.playError'));
        setPlayingFilename(null);
      };
      audio.play();
      audioRef.current = audio;
      setPlayingFilename(preset.filename);
    }
  };

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const getLanguageLabel = (code: string) => {
    if (code === 'zh') return t('presetVoice.languageChinese');
    if (code === 'en') return t('presetVoice.languageEnglish');
    if (code === 'in') return t('presetVoice.languageIndian');
    return code.toUpperCase();
  };

  const getGenderLabel = (gender: string) => {
    if (gender === 'man') return t('presetVoice.genderMale');
    if (gender === 'woman') return t('presetVoice.genderFemale');
    return gender;
  };

  return (
    <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{t('presetVoice.title')}</h2>
            <p className="text-sm text-gray-500">{t('presetVoice.subtitle')}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-500"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-3 border-b border-gray-200 flex flex-wrap items-center gap-3">
          {/* Add Button */}
          <button
            onClick={() => setShowAddForm(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t('presetVoice.add')}
          </button>

          {/* Delete Selected */}
          {selectedFilenames.size > 0 && (
            <button
              onClick={handleBatchDelete}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              {t('presetVoice.deleteSelected')} ({selectedFilenames.size})
            </button>
          )}

          <div className="flex-1" />

          {/* Filters */}
          <select
            value={languageFilter || ''}
            onChange={(e) => setLanguageFilter(e.target.value || null)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">{t('presetVoice.allLanguages')}</option>
            <option value="en">{t('presetVoice.languageEnglish')}</option>
            <option value="zh">{t('presetVoice.languageChinese')}</option>
            <option value="in">{t('presetVoice.languageIndian')}</option>
          </select>

          <select
            value={genderFilter || ''}
            onChange={(e) => setGenderFilter(e.target.value as "man" | "woman" | null || null)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">{t('presetVoice.allGenders')}</option>
            <option value="man">{t('presetVoice.genderMale')}</option>
            <option value="woman">{t('presetVoice.genderFemale')}</option>
          </select>

          <select
            value={hasBgmFilter === null ? '' : hasBgmFilter ? 'true' : 'false'}
            onChange={(e) => {
              if (e.target.value === '') setHasBgmFilter(null);
              else setHasBgmFilter(e.target.value === 'true');
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">{t('presetVoice.allTypes')}</option>
            <option value="true">{t('presetVoice.withBgm')}</option>
            <option value="false">{t('presetVoice.withoutBgm')}</option>
          </select>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
          ) : presets.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <p>{t('presetVoice.noPresets')}</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="mt-4 text-blue-500 hover:text-blue-600"
              >
                {t('presetVoice.addFirst')}
              </button>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 px-2 text-left w-10">
                    <input
                      type="checkbox"
                      checked={selectedFilenames.size === presets.length && presets.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="py-3 px-2 text-left font-medium text-gray-700">{t('presetVoice.name')}</th>
                  <th className="py-3 px-2 text-left font-medium text-gray-700">{t('presetVoice.language')}</th>
                  <th className="py-3 px-2 text-left font-medium text-gray-700">{t('presetVoice.gender')}</th>
                  <th className="py-3 px-2 text-left font-medium text-gray-700">{t('presetVoice.bgm')}</th>
                  <th className="py-3 px-2 text-right font-medium text-gray-700">{t('presetVoice.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {presets.map((preset) => (
                  <tr key={preset.filename} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-2">
                      <input
                        type="checkbox"
                        checked={selectedFilenames.has(preset.filename)}
                        onChange={() => handleSelectOne(preset.filename)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="py-3 px-2 font-medium text-gray-900">{preset.name}</td>
                    <td className="py-3 px-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                        {getLanguageLabel(preset.language)}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        preset.gender === 'woman'
                          ? 'bg-pink-100 text-pink-700'
                          : 'bg-sky-100 text-sky-700'
                      }`}>
                        {getGenderLabel(preset.gender)}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      {preset.has_bgm ? (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                          {t('presetVoice.withBgm')}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handlePlayPreview(preset)}
                          className={`p-2 rounded-lg transition-colors ${
                            playingFilename === preset.filename
                              ? 'bg-blue-100 text-blue-600'
                              : 'hover:bg-gray-100 text-gray-500'
                          }`}
                          title={playingFilename === preset.filename ? t('presetVoice.stop') : t('presetVoice.play')}
                        >
                          {playingFilename === preset.filename ? (
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M8 5v14l11-7z" />
                            </svg>
                          )}
                        </button>
                        <button
                          onClick={() => handleDelete(preset)}
                          className="p-2 hover:bg-red-50 rounded-lg text-red-600"
                          title={t('common.delete')}
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {total > 0 && (
          <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {t('presetVoice.showingItems')
                .replace('{start}', String(offset + 1))
                .replace('{end}', String(Math.min(offset + limit, total)))
                .replace('{total}', String(total))}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
              <button
                onClick={() => setPage(currentPage - 1)}
                disabled={currentPage === 0}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                {t('presetVoice.previous')}
              </button>
              <span className="text-sm text-gray-600">
                {currentPage + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage(currentPage + 1)}
                disabled={currentPage >= totalPages - 1}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                {t('presetVoice.next')}
              </button>
            </div>
          </div>
        )}

        {/* Add Form Modal */}
        {showAddForm && (
          <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-10 rounded-xl">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">{t('presetVoice.addTitle')}</h3>
              <form onSubmit={handleAddSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('presetVoice.name')} *
                  </label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder={t('presetVoice.namePlaceholder')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {t('presetVoice.nameHint')}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {t('presetVoice.language')} *
                    </label>
                    <select
                      value={newLanguage}
                      onChange={(e) => setNewLanguage(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="en">{t('presetVoice.languageEnglish')}</option>
                      <option value="zh">{t('presetVoice.languageChinese')}</option>
                      <option value="in">{t('presetVoice.languageIndian')}</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {t('presetVoice.gender')} *
                    </label>
                    <select
                      value={newGender}
                      onChange={(e) => setNewGender(e.target.value as "man" | "woman")}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="woman">{t('presetVoice.genderFemale')}</option>
                      <option value="man">{t('presetVoice.genderMale')}</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newHasBgm}
                      onChange={(e) => setNewHasBgm(e.target.checked)}
                      className="rounded border-gray-300 text-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      {t('presetVoice.hasBgm')}
                    </span>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('presetVoice.voiceFile')} *
                  </label>
                  <input
                    type="file"
                    accept=".wav,.mp3,.m4a,.flac,.webm,.ogg,.aac"
                    onChange={(e) => setNewVoiceFile(e.target.files?.[0] || null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {t('presetVoice.supportedFormats')}
                  </p>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddForm(false);
                      setNewName("");
                      setNewLanguage("en");
                      setNewGender("woman");
                      setNewHasBgm(false);
                      setNewVoiceFile(null);
                    }}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    {t('common.cancel')}
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !newName.trim() || !newVoiceFile}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? t('common.loading') : t('presetVoice.create')}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PresetVoiceManager({ isOpen, onClose }: PresetVoiceManagerProps) {
  if (!isOpen) return null;

  return (
    <PresetVoiceProvider>
      <PresetVoiceManagerContent onClose={onClose} />
    </PresetVoiceProvider>
  );
}
