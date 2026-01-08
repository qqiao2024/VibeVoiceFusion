'use client';

import React, { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLanguage } from '@/lib/i18n/LanguageContext';
import { api } from '@/lib/api';
import type { QuickGenerate, QuickGenerateMode, QuickGenerateItem } from '@/types/quickGenerate';
import type { OffloadingMode, OffloadingPreset } from '@/types/generation';
import type { PresetVoice, PresetLanguage } from '@/types/preset';
import QuickGenerateHistory from '@/components/QuickGenerateHistory';

// Preset information for offloading configurations
const PRESET_INFO = {
  balanced: {
    vram_savings: '~5GB',
    slowdown: '~2.0x',
    gpu_layers: 12,
  },
  aggressive: {
    vram_savings: '~6GB',
    slowdown: '~2.5x',
    gpu_layers: 8,
  },
  extreme: {
    vram_savings: '~7GB',
    slowdown: '~3.5x',
    gpu_layers: 4,
  },
};

function QuickGenerateContent() {
  const { t } = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Voice source state - supports up to 4 voice prompts
  const MAX_VOICE_PROMPTS = 4;
  type VoiceSource = { type: 'upload'; file: File } | { type: 'preset'; preset: PresetVoice };
  const [voiceSources, setVoiceSources] = useState<VoiceSource[]>([]);
  const [activeVoiceSlot, setActiveVoiceSlot] = useState<number>(0);
  type VoiceSourceTab = 'upload' | 'preset';
  const [voiceSourceTab, setVoiceSourceTab] = useState<VoiceSourceTab>('upload');
  const [uploadedAudioUrls, setUploadedAudioUrls] = useState<(string | null)[]>([]);
  const uploadedAudioRef = useRef<HTMLAudioElement | null>(null);
  const [playingVoiceIndex, setPlayingVoiceIndex] = useState<number | null>(null);
  const fileInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Preset voice state
  const [presets, setPresets] = useState<PresetVoice[]>([]);
  const [presetLanguages, setPresetLanguages] = useState<PresetLanguage[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [selectedGender, setSelectedGender] = useState<string>('');
  const [showBgmOnly, setShowBgmOnly] = useState<boolean | null>(null);
  const [playingPreset, setPlayingPreset] = useState<string | null>(null);
  const presetAudioRef = useRef<HTMLAudioElement | null>(null);

  // Form state
  const [text, setText] = useState('');
  const [seeds, setSeeds] = useState(() => Math.floor(Math.random() * 1000000));
  const [batchSize, setBatchSize] = useState(1);
  const [cfgScale, setCfgScale] = useState(1.3);
  const [modelDtype, setModelDtype] = useState<'bf16' | 'float8_e4m3fn'>('bf16');

  // Offloading state
  const [offloadingEnabled, setOffloadingEnabled] = useState(false);
  const [offloadingMode, setOffloadingMode] = useState<OffloadingMode>('preset');
  const [offloadingPreset, setOffloadingPreset] = useState<OffloadingPreset>('balanced');
  const [manualGpuLayers, setManualGpuLayers] = useState(20);

  // Generation state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentGeneration, setCurrentGeneration] = useState<QuickGenerate | null>(null);
  const [detectedMode, setDetectedMode] = useState<QuickGenerateMode | null>(null);

  // Auto-detect mode from text
  useEffect(() => {
    if (!text.trim()) {
      setDetectedMode(null);
      return;
    }

    // Check if any line starts with "Speaker N:" pattern (e.g., "Speaker 1:", "Speaker 2:")
    // This matches the backend detection logic in backend/models/quick_generate.py
    const lines = text.trim().split('\n');
    const speakerPattern = /^Speaker\s+\d+\s*:/i;
    const hasDialogue = lines.some(line => speakerPattern.test(line.trim()));
    setDetectedMode(hasDialogue ? 'dialogue' : 'narration');
  }, [text]);

  // Load preset languages on mount
  useEffect(() => {
    api.listPresetLanguages()
      .then(response => setPresetLanguages(response.languages))
      .catch(err => console.error('Failed to load preset languages:', err));
  }, []);

  // Load presets when filters change
  useEffect(() => {
    const loadPresets = async () => {
      setPresetsLoading(true);
      try {
        const response = await api.listPresetVoices({
          language: selectedLanguage || undefined,
          gender: selectedGender as 'man' | 'woman' | undefined,
          has_bgm: showBgmOnly ?? undefined,
        });
        setPresets(response.presets);
      } catch (err) {
        console.error('Failed to load presets:', err);
      } finally {
        setPresetsLoading(false);
      }
    };
    loadPresets();
  }, [selectedLanguage, selectedGender, showBgmOnly]);

  // Create/revoke object URLs for uploaded audio previews
  useEffect(() => {
    const newUrls: (string | null)[] = [];
    const urlsToRevoke: string[] = [];

    voiceSources.forEach((source, index) => {
      if (source.type === 'upload') {
        const url = URL.createObjectURL(source.file);
        newUrls[index] = url;
        urlsToRevoke.push(url);
      } else {
        newUrls[index] = null;
      }
    });

    setUploadedAudioUrls(newUrls);

    return () => {
      urlsToRevoke.forEach(url => URL.revokeObjectURL(url));
    };
  }, [voiceSources]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      uploadedAudioRef.current?.pause();
      presetAudioRef.current?.pause();
    };
  }, []);

  // Poll for generation status
  useEffect(() => {
    if (!currentGeneration) return;

    const isInProgress = currentGeneration.status === 'pending' ||
                         currentGeneration.status === 'preprocessing' ||
                         currentGeneration.status === 'inferencing';

    if (!isInProgress) return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.getQuickGeneration(currentGeneration.request_id);
        setCurrentGeneration(updated);

        // Stop polling if completed or failed
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Failed to poll generation status:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentGeneration?.request_id, currentGeneration?.status]);

  // Check for existing generation on mount
  useEffect(() => {
    const requestId = searchParams.get('request_id');
    if (requestId) {
      api.getQuickGeneration(requestId)
        .then(gen => setCurrentGeneration(gen))
        .catch(err => console.error('Failed to load generation:', err));
    } else {
      // Check for current running generation
      api.getCurrentQuickGeneration()
        .then(response => {
          if (response.generation) {
            setCurrentGeneration(response.generation);
          }
        })
        .catch(err => console.error('Failed to check current generation:', err));
    }
  }, [searchParams]);

  // Handle file selection for a specific slot
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, slotIndex?: number) => {
    const file = e.target.files?.[0];
    if (file) {
      addVoiceSource({ type: 'upload', file }, slotIndex);
    }
  };

  const handleDrop = (e: React.DragEvent, slotIndex?: number) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('audio/')) {
      addVoiceSource({ type: 'upload', file }, slotIndex);
    }
  };

  // Add a voice source to the list
  const addVoiceSource = (source: VoiceSource, replaceIndex?: number) => {
    setVoiceSources(prev => {
      if (replaceIndex !== undefined && replaceIndex < prev.length) {
        // Replace existing slot
        const newSources = [...prev];
        newSources[replaceIndex] = source;
        return newSources;
      } else if (prev.length < MAX_VOICE_PROMPTS) {
        // Add new slot
        return [...prev, source];
      }
      return prev;
    });
  };

  // Remove a voice source by index
  const removeVoiceSource = (index: number) => {
    setVoiceSources(prev => prev.filter((_, i) => i !== index));
    if (playingVoiceIndex === index) {
      uploadedAudioRef.current?.pause();
      presetAudioRef.current?.pause();
      setPlayingVoiceIndex(null);
    }
  };

  // Toggle voice preview playback
  const toggleVoicePreview = (index: number) => {
    const source = voiceSources[index];
    if (!source) return;

    if (playingVoiceIndex === index) {
      // Stop playing
      uploadedAudioRef.current?.pause();
      presetAudioRef.current?.pause();
      setPlayingVoiceIndex(null);
    } else {
      // Stop any current playback
      uploadedAudioRef.current?.pause();
      presetAudioRef.current?.pause();

      // Start new playback
      if (source.type === 'upload' && uploadedAudioUrls[index]) {
        if (uploadedAudioRef.current) {
          uploadedAudioRef.current.src = uploadedAudioUrls[index]!;
          uploadedAudioRef.current.play();
          setPlayingVoiceIndex(index);
        }
      } else if (source.type === 'preset') {
        if (presetAudioRef.current) {
          presetAudioRef.current.src = api.getPresetPreviewUrl(source.preset.filename);
          presetAudioRef.current.play();
          setPlayingVoiceIndex(index);
        }
      }
    }
  };

  // Handle audio ended
  const handleAudioEnded = () => {
    setPlayingVoiceIndex(null);
  };

  // Toggle preset audio preview (for selection grid)
  const togglePresetPreview = (preset: PresetVoice) => {
    if (playingPreset === preset.filename) {
      presetAudioRef.current?.pause();
      setPlayingPreset(null);
    } else {
      if (presetAudioRef.current) {
        presetAudioRef.current.src = api.getPresetPreviewUrl(preset.filename);
        presetAudioRef.current.play();
        setPlayingPreset(preset.filename);
      }
    }
  };

  // Handle preset audio ended
  const handlePresetAudioEnded = () => {
    setPlayingPreset(null);
    setPlayingVoiceIndex(null);
  };

  // Select a preset voice and add to voice sources
  const handleSelectPreset = (preset: PresetVoice) => {
    addVoiceSource({ type: 'preset', preset });
  };

  // Get display name for a voice source
  const getVoiceSourceDisplayName = (source: VoiceSource): string => {
    if (source.type === 'upload') {
      return source.file.name;
    } else {
      return source.preset.display_name;
    }
  };

  // Get language display name
  const getLanguageDisplayName = (lang: string): string => {
    switch (lang) {
      case 'en': return 'English';
      case 'zh': return 'Chinese';
      case 'in': return 'Indian English';
      default: return lang.toUpperCase();
    }
  };

  const generateRandomSeed = () => {
    setSeeds(Math.floor(Math.random() * 1000000));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate at least one voice source
    if (voiceSources.length === 0) {
      setError(t('quickGenerate.errorVoiceRequired'));
      return;
    }

    if (!text.trim()) {
      setError(t('quickGenerate.errorTextRequired'));
      return;
    }

    setLoading(true);

    try {
      // Convert voice sources to File objects
      const filesToUpload: File[] = [];

      for (const source of voiceSources) {
        if (source.type === 'upload') {
          filesToUpload.push(source.file);
        } else {
          // Fetch preset audio as blob and create File object
          const presetUrl = api.getPresetPreviewUrl(source.preset.filename);
          const response = await fetch(presetUrl);
          if (!response.ok) {
            throw new Error(t('quickGenerate.errorLoadPreset'));
          }
          const blob = await response.blob();
          filesToUpload.push(new File([blob], source.preset.filename, { type: 'audio/wav' }));
        }
      }

      const offloading = offloadingEnabled ? {
        enabled: true,
        mode: offloadingMode,
        ...(offloadingMode === 'preset'
          ? { preset: offloadingPreset }
          : { num_gpu_layers: manualGpuLayers }
        )
      } : undefined;

      const apiResponse = await api.startQuickGeneration({
        voice_files: filesToUpload,
        text: text.trim(),
        seeds,
        batch_size: batchSize,
        cfg_scale: cfgScale,
        model_dtype: modelDtype,
        offloading
      });

      // Load the full generation state
      const generation = await api.getQuickGeneration(apiResponse.request_id);
      setCurrentGeneration(generation);

      // Update URL with request_id
      router.replace(`/quick-generate?request_id=${apiResponse.request_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('quickGenerate.errorGeneric');
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleNewGeneration = () => {
    setCurrentGeneration(null);
    router.replace('/quick-generate');
  };

  const handleSelectGeneration = useCallback((gen: QuickGenerate) => {
    setCurrentGeneration(gen);
    router.replace(`/quick-generate?request_id=${gen.request_id}`);
  }, [router]);

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  // Render generation result
  const renderGenerationResult = () => {
    if (!currentGeneration) return null;

    const isInProgress = currentGeneration.status === 'pending' ||
                         currentGeneration.status === 'preprocessing' ||
                         currentGeneration.status === 'inferencing';

    const isCompleted = currentGeneration.status === 'completed';
    const isFailed = currentGeneration.status === 'failed';

    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {isInProgress ? t('quickGenerate.generating') :
             isCompleted ? t('quickGenerate.completed') :
             t('quickGenerate.failed')}
          </h2>
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
            isCompleted ? 'bg-green-100 text-green-800' :
            isFailed ? 'bg-red-100 text-red-800' :
            'bg-blue-100 text-blue-800'
          }`}>
            {currentGeneration.detected_mode === 'dialogue' ?
              t('quickGenerate.dialogueMode') :
              t('quickGenerate.narrationMode')}
          </span>
        </div>

        {/* Progress bar */}
        {isInProgress && (
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>{t('quickGenerate.progress')}</span>
              <span>{Math.round(currentGeneration.percentage || 0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${currentGeneration.percentage || 0}%` }}
              />
            </div>
            {currentGeneration.is_multi_generation && currentGeneration.current_batch_index !== undefined && (
              <p className="text-xs text-gray-500 mt-1">
                {t('quickGenerate.batchProgress')
                  .replace('{current}', String((currentGeneration.current_batch_index || 0) + 1))
                  .replace('{total}', String(currentGeneration.batch_size))}
              </p>
            )}
          </div>
        )}

        {/* Error message */}
        {isFailed && currentGeneration.error_message && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{currentGeneration.error_message}</p>
          </div>
        )}

        {/* Completed results */}
        {isCompleted && (
          <div className="space-y-4">
            {/* Single generation or multi-generation results */}
            {currentGeneration.is_multi_generation && currentGeneration.details?.generation_items ? (
              <div className="space-y-3">
                {currentGeneration.details.generation_items.map((item: QuickGenerateItem, index: number) => (
                  <div key={index} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {t('quickGenerate.generationItem').replace('{index}', String(index + 1))}
                      </span>
                      <span className="text-xs text-gray-500">
                        {t('quickGenerate.seed')}: {item.seeds}
                      </span>
                    </div>
                    <audio
                      controls
                      className="w-full mb-2"
                      src={api.getQuickGenerationItemDownloadUrl(currentGeneration.request_id, index)}
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>
                        {item.audio_duration_seconds ?
                          t('quickGenerate.duration').replace('{duration}', formatDuration(item.audio_duration_seconds)) :
                          ''}
                      </span>
                      <a
                        href={`${api.getQuickGenerationItemDownloadUrl(currentGeneration.request_id, index)}?download=true`}
                        className="text-blue-600 hover:underline"
                      >
                        {t('quickGenerate.download')}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div>
                <audio
                  controls
                  className="w-full mb-2"
                  src={api.getQuickGenerationDownloadUrl(currentGeneration.request_id)}
                />
                <div className="flex justify-end">
                  <a
                    href={`${api.getQuickGenerationDownloadUrl(currentGeneration.request_id)}?download=true`}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    {t('quickGenerate.download')}
                  </a>
                </div>
              </div>
            )}

            {/* New generation button */}
            <button
              onClick={handleNewGeneration}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              {t('quickGenerate.newGeneration')}
            </button>
          </div>
        )}

        {/* In progress - show spinner */}
        {isInProgress && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}
      </div>
    );
  };

  // Render form
  const renderForm = () => (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Hidden audio elements for preview */}
      <audio ref={uploadedAudioRef} onEnded={handleAudioEnded} className="hidden" />
      <audio ref={presetAudioRef} onEnded={handlePresetAudioEnded} className="hidden" />

      {/* Voice Sources */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">
            {t('quickGenerate.voiceSample')} <span className="text-red-500">*</span>
          </label>
          <span className="text-xs text-gray-500">
            {voiceSources.length}/{MAX_VOICE_PROMPTS} {t('quickGenerate.voicesSelected')}
          </span>
        </div>

        {/* Selected voice sources list */}
        {voiceSources.length > 0 && (
          <div className="space-y-2 mb-4">
            {voiceSources.map((source, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg"
              >
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-600 text-white text-xs font-medium">
                  {index + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-green-800 truncate">
                    {getVoiceSourceDisplayName(source)}
                  </p>
                  <p className="text-xs text-green-600">
                    {source.type === 'upload' ? t('quickGenerate.uploadTab') : t('quickGenerate.presetTab')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleVoicePreview(index)}
                  className="p-1.5 rounded-full bg-green-100 hover:bg-green-200 text-green-700 transition-colors"
                  title={playingVoiceIndex === index ? t('preset.stop') : t('preset.preview')}
                >
                  {playingVoiceIndex === index ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => removeVoiceSource(index)}
                  className="p-1.5 rounded-full bg-gray-100 hover:bg-red-100 text-gray-500 hover:text-red-500 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add voice area (only show if less than max) */}
        {voiceSources.length < MAX_VOICE_PROMPTS && (
          <>
            {/* Voice Source Tabs */}
            <div className="flex border-b border-gray-200 mb-4">
              <button
                type="button"
                onClick={() => setVoiceSourceTab('upload')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  voiceSourceTab === 'upload'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {t('quickGenerate.uploadTab')}
              </button>
              <button
                type="button"
                onClick={() => setVoiceSourceTab('preset')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  voiceSourceTab === 'preset'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {t('quickGenerate.presetTab')}
              </button>
            </div>

            {/* Upload Tab Content */}
            {voiceSourceTab === 'upload' && (
              <div>
                <div
                  className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors border-gray-300 hover:border-blue-400"
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={(e) => handleDrop(e)}
                  onDragOver={(e) => e.preventDefault()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    onChange={(e) => handleFileSelect(e)}
                    className="hidden"
                  />
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="mt-2 text-sm text-gray-600">
                    {t('quickGenerate.dropOrClick')}
                  </p>
                  <p className="text-xs text-gray-500">
                    WAV, MP3, M4A, FLAC, WEBM
                  </p>
                </div>
              </div>
            )}

            {/* Preset Tab Content */}
            {voiceSourceTab === 'preset' && (
              <div className="space-y-3">
                {/* Filters */}
                <div className="flex flex-wrap gap-2">
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">{t('preset.allLanguages')}</option>
                    {presetLanguages.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.name} ({lang.count})
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedGender}
                    onChange={(e) => setSelectedGender(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">{t('preset.allGenders')}</option>
                    <option value="woman">{t('preset.female')}</option>
                    <option value="man">{t('preset.male')}</option>
                  </select>

                  <select
                    value={showBgmOnly === null ? '' : showBgmOnly.toString()}
                    onChange={(e) => {
                      const value = e.target.value;
                      setShowBgmOnly(value === '' ? null : value === 'true');
                    }}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">{t('preset.allTypes')}</option>
                    <option value="false">{t('preset.withoutBgm')}</option>
                    <option value="true">{t('preset.withBgm')}</option>
                  </select>
                </div>

                {/* Preset grid */}
                {presetsLoading ? (
                  <div className="flex justify-center py-6">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  </div>
                ) : presets.length === 0 ? (
                  <div className="text-center py-6 text-gray-500">
                    <p>{t('preset.noPresetsFound')}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                    {presets.map((preset) => {
                      const isAlreadySelected = voiceSources.some(
                        s => s.type === 'preset' && s.preset.filename === preset.filename
                      );
                      return (
                        <div
                          key={preset.filename}
                          className={`border rounded-lg p-3 transition-all ${
                            isAlreadySelected
                              ? 'border-green-400 bg-green-50 opacity-60 cursor-not-allowed'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50 cursor-pointer'
                          }`}
                          onClick={() => !isAlreadySelected && handleSelectPreset(preset)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="min-w-0 flex-1">
                              <h4 className="font-medium text-gray-900 text-sm truncate">{preset.name}</h4>
                              <p className="text-xs text-gray-500 truncate">
                                {getLanguageDisplayName(preset.language)}
                                {' - '}
                                {preset.gender === 'woman' ? t('preset.female') : t('preset.male')}
                              </p>
                            </div>
                            <div className="flex items-center gap-1 ml-2">
                              {preset.has_bgm && (
                                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                  BGM
                                </span>
                              )}
                              {isAlreadySelected ? (
                                <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              ) : (
                                <button
                                  type="button"
                                  onClick={(e) => { e.stopPropagation(); togglePresetPreview(preset); }}
                                  className="p-1 rounded-full hover:bg-gray-200 text-gray-500 transition-colors"
                                >
                                  {playingPreset === preset.filename ? (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                    </svg>
                                  ) : (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                  )}
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Text Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t('quickGenerate.textToGenerate')} <span className="text-red-500">*</span>
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('quickGenerate.textPlaceholder')}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[120px]"
          required
        />
        {detectedMode && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-gray-500">{t('quickGenerate.detectedMode')}:</span>
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
              detectedMode === 'dialogue' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
            }`}>
              {detectedMode === 'dialogue' ? t('quickGenerate.dialogueMode') : t('quickGenerate.narrationMode')}
            </span>
          </div>
        )}
        <p className="text-xs text-gray-500 mt-1">
          {t('quickGenerate.textHint')}
        </p>
      </div>

      {/* Seed */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t('quickGenerate.seed')}
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            value={seeds}
            onChange={(e) => setSeeds(parseInt(e.target.value) || 0)}
            min="0"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={generateRandomSeed}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title={t('quickGenerate.randomSeed')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" className="w-5 h-5">
              <path d="M302.87 255.5a47.37 47.37 0 1 1-47.37-47.37 47.37 47.37 0 0 1 47.37 47.37zM128.5 81.18a47.37 47.37 0 1 0 47.41 47.32 47.37 47.37 0 0 0-47.41-47.32zm253.91 0a47.37 47.37 0 1 0 47.41 47.32 47.37 47.37 0 0 0-47.32-47.32zM128.5 335.09a47.37 47.37 0 1 0 47.41 47.41 47.37 47.37 0 0 0-47.41-47.41zm253.91 0a47.37 47.37 0 1 0 47.41 47.41 47.37 47.37 0 0 0-47.32-47.41zm102 92.93a56.48 56.48 0 0 1-56.39 56.48h-344a56.48 56.48 0 0 1-56.52-56.48v-344A56.48 56.48 0 0 1 83.98 27.5h344a56.48 56.48 0 0 1 56.52 56.48zm-20-344a36.48 36.48 0 0 0-36.39-36.52h-344A36.48 36.48 0 0 0 47.5 83.98v344a36.48 36.48 0 0 0 36.48 36.52h344a36.48 36.48 0 0 0 36.52-36.48z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </div>

      {/* Batch Size */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t('quickGenerate.numberOfGenerations')}: {batchSize}
        </label>
        <input
          type="range"
          min="1"
          max="20"
          value={batchSize}
          onChange={(e) => setBatchSize(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1</span>
          <span>20</span>
        </div>
      </div>

      {/* Advanced Settings (Collapsible) */}
      <details className="border border-gray-200 rounded-lg">
        <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50">
          {t('quickGenerate.advancedSettings')}
        </summary>
        <div className="px-4 pb-4 space-y-4">
          {/* Model Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('generation.modelType')}
            </label>
            <select
              value={modelDtype}
              onChange={(e) => setModelDtype(e.target.value as 'bf16' | 'float8_e4m3fn')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="bf16">{t('generation.bf16Recommended')}</option>
              <option value="float8_e4m3fn">float8_e4m3fn</option>
            </select>
          </div>

          {/* CFG Scale */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('generation.cfgScale')}: {cfgScale}
            </label>
            <input
              type="range"
              min="0.1"
              max="10"
              step="0.1"
              value={cfgScale}
              onChange={(e) => setCfgScale(parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>

          {/* Offloading */}
          <div className="border border-gray-200 rounded-lg p-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={offloadingEnabled}
                onChange={(e) => setOffloadingEnabled(e.target.checked)}
                className="w-4 h-4 text-blue-500 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">{t('generation.enableOffloading')}</span>
            </label>

            {offloadingEnabled && (
              <div className="mt-3 space-y-3">
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="preset"
                      checked={offloadingMode === 'preset'}
                      onChange={(e) => setOffloadingMode(e.target.value as OffloadingMode)}
                      className="w-4 h-4 text-blue-500 focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{t('generation.presetRecommended')}</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="manual"
                      checked={offloadingMode === 'manual'}
                      onChange={(e) => setOffloadingMode(e.target.value as OffloadingMode)}
                      className="w-4 h-4 text-blue-500 focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{t('generation.manualAdvanced')}</span>
                  </label>
                </div>

                {offloadingMode === 'preset' && (
                  <select
                    value={offloadingPreset}
                    onChange={(e) => setOffloadingPreset(e.target.value as OffloadingPreset)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="balanced">{t('generation.balanced')} ({PRESET_INFO.balanced.vram_savings})</option>
                    <option value="aggressive">{t('generation.aggressive')} ({PRESET_INFO.aggressive.vram_savings})</option>
                    <option value="extreme">{t('generation.extreme')} ({PRESET_INFO.extreme.vram_savings})</option>
                  </select>
                )}

                {offloadingMode === 'manual' && (
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      {t('generation.gpuLayers')}: {manualGpuLayers}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="28"
                      value={manualGpuLayers}
                      onChange={(e) => setManualGpuLayers(parseInt(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </details>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || voiceSources.length === 0 || !text.trim()}
        className="w-full px-4 py-3 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            {t('quickGenerate.starting')}
          </span>
        ) : (
          t('quickGenerate.generateVoice')
        )}
      </button>
    </form>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center space-x-2 mb-1">
          <h1 className="text-2xl font-bold text-gray-900">{t('quickGenerate.pageTitle')}</h1>
          <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
            {t('quickGenerate.quickMode')}
          </span>
        </div>
        <p className="text-sm text-gray-500">{t('quickGenerate.pageSubtitle')}</p>
      </header>

      {/* Main Content - Two Column Layout */}
      <div className="flex-1 overflow-hidden bg-gray-50">
        <div className="h-full grid grid-cols-2 gap-6 p-6">
          {/* Left Column - Generation History */}
          <div className="bg-white rounded-lg shadow-sm p-6 overflow-hidden flex flex-col">
            <QuickGenerateHistory
              onSelectGeneration={handleSelectGeneration}
              currentGenerationId={currentGeneration?.request_id}
            />
          </div>

          {/* Right Column - Current Generation or Form */}
          <div className="flex flex-col gap-6 overflow-y-auto">
            {/* Current Generation Status (if active) */}
            {currentGeneration && renderGenerationResult()}

            {/* Generation Form (if no active generation) */}
            {!currentGeneration && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                {renderForm()}
              </div>
            )}

            {/* Info Card */}
            {!currentGeneration && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">{t('quickGenerate.howItWorks')}</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>{t('quickGenerate.step1')}</li>
                  <li>{t('quickGenerate.step2')}</li>
                  <li>{t('quickGenerate.step3')}</li>
                  <li>{t('quickGenerate.step4')}</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function QuickGeneratePage() {
  return (
    <Suspense fallback={
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    }>
      <QuickGenerateContent />
    </Suspense>
  );
}
