"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import type { PresetVoice, PresetLanguage } from "@/types/preset";

interface PresetVoiceSelectorProps {
  onSelect: (preset: PresetVoice) => Promise<void>;
}

export default function PresetVoiceSelector({ onSelect }: PresetVoiceSelectorProps) {
  const { t } = useLanguage();
  const [presets, setPresets] = useState<PresetVoice[]>([]);
  const [languages, setLanguages] = useState<PresetLanguage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [selectedGender, setSelectedGender] = useState<string>('');
  const [showBgmOnly, setShowBgmOnly] = useState<boolean | null>(null);

  // Audio preview
  const [playingPreset, setPlayingPreset] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    loadLanguages();
    loadPresets();
  }, []);

  useEffect(() => {
    loadPresets();
  }, [selectedLanguage, selectedGender, showBgmOnly]);

  const loadPresets = async () => {
    try {
      setLoading(true);
      const response = await api.listPresetVoices({
        language: selectedLanguage || undefined,
        gender: selectedGender as 'man' | 'woman' | undefined,
        has_bgm: showBgmOnly ?? undefined,
      });
      setPresets(response.presets);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.unknown'));
    } finally {
      setLoading(false);
    }
  };

  const loadLanguages = async () => {
    try {
      const response = await api.listPresetLanguages();
      setLanguages(response.languages);
    } catch (err) {
      console.error('Failed to load languages:', err);
    }
  };

  const handlePreview = (preset: PresetVoice) => {
    if (playingPreset === preset.filename) {
      // Stop playing
      audioRef.current?.pause();
      setPlayingPreset(null);
    } else {
      // Start playing
      if (audioRef.current) {
        audioRef.current.src = api.getPresetPreviewUrl(preset.filename);
        audioRef.current.play();
        setPlayingPreset(preset.filename);
      }
    }
  };

  const handleSelect = async (preset: PresetVoice) => {
    setSelecting(preset.filename);
    setError(null);
    try {
      await onSelect(preset);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('speaker.createError'));
    } finally {
      setSelecting(null);
    }
  };

  const handleAudioEnded = () => {
    setPlayingPreset(null);
  };

  const getLanguageDisplayName = (lang: string): string => {
    switch (lang) {
      case 'en':
        return 'English';
      case 'zh':
        return 'Chinese';
      case 'in':
        return 'Indian English';
      default:
        return lang.toUpperCase();
    }
  };

  return (
    <div className="space-y-4">
      {/* Hidden audio element for preview */}
      <audio ref={audioRef} onEnded={handleAudioEnded} className="hidden" />

      {/* Info text */}
      <p className="text-sm text-gray-500">
        {t('preset.selectPresetToCreate')}
      </p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 pb-4 border-b border-gray-200">
        {/* Language filter */}
        <select
          value={selectedLanguage}
          onChange={(e) => setSelectedLanguage(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">{t('preset.allLanguages')}</option>
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name} ({lang.count})
            </option>
          ))}
        </select>

        {/* Gender filter */}
        <select
          value={selectedGender}
          onChange={(e) => setSelectedGender(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">{t('preset.allGenders')}</option>
          <option value="woman">{t('preset.female')}</option>
          <option value="man">{t('preset.male')}</option>
        </select>

        {/* BGM filter */}
        <select
          value={showBgmOnly === null ? '' : showBgmOnly.toString()}
          onChange={(e) => {
            const value = e.target.value;
            setShowBgmOnly(value === '' ? null : value === 'true');
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">{t('preset.allTypes')}</option>
          <option value="false">{t('preset.withoutBgm')}</option>
          <option value="true">{t('preset.withBgm')}</option>
        </select>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Preset grid */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : presets.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>{t('preset.noPresetsFound')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {presets.map((preset) => (
            <div
              key={preset.filename}
              className="border border-gray-200 rounded-lg p-4 bg-white hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-medium text-gray-900">{preset.name}</h4>
                  <p className="text-sm text-gray-500">
                    {getLanguageDisplayName(preset.language)}
                    {' - '}
                    {preset.gender === 'woman' ? t('preset.female') : t('preset.male')}
                  </p>
                </div>
                {preset.has_bgm && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    BGM
                  </span>
                )}
              </div>

              <div className="flex gap-2">
                {/* Preview button */}
                <button
                  onClick={() => handlePreview(preset)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  {playingPreset === preset.filename ? (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                      </svg>
                      {t('preset.stop')}
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {t('preset.preview')}
                    </>
                  )}
                </button>

                {/* Select button */}
                <button
                  onClick={() => handleSelect(preset)}
                  disabled={selecting !== null}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {selecting === preset.filename ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {t('common.loading')}
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {t('preset.select')}
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
