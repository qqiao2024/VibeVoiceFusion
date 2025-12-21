"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { api } from "@/lib/api";
import type { PresetVoice, PresetLanguage } from "@/types/preset";

interface PresetVoiceContextType {
  presets: PresetVoice[];
  total: number;
  loading: boolean;
  error: string | null;
  languages: PresetLanguage[];

  // Pagination state
  offset: number;
  limit: number;

  // Filter state
  languageFilter: string | null;
  genderFilter: "man" | "woman" | null;
  hasBgmFilter: boolean | null;

  // Actions
  loadPresets: () => Promise<void>;
  loadLanguages: () => Promise<void>;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  setLanguageFilter: (language: string | null) => void;
  setGenderFilter: (gender: "man" | "woman" | null) => void;
  setHasBgmFilter: (hasBgm: boolean | null) => void;
  createPreset: (data: {
    name: string;
    language: string;
    gender: "man" | "woman";
    has_bgm: boolean;
    voice_file: File;
  }) => Promise<PresetVoice>;
  deletePreset: (filename: string) => Promise<boolean>;
  batchDeletePresets: (filenames: string[]) => Promise<{
    deleted: string[];
    failed: string[];
  }>;
  refresh: () => Promise<void>;
}

const PresetVoiceContext = createContext<PresetVoiceContextType | undefined>(undefined);

const DEFAULT_LIMIT = 10;

export function PresetVoiceProvider({ children }: { children: ReactNode }) {
  const [presets, setPresets] = useState<PresetVoice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [languages, setLanguages] = useState<PresetLanguage[]>([]);

  // Pagination
  const [offset, setOffset] = useState(0);
  const [limit, setLimitState] = useState(DEFAULT_LIMIT);

  // Filters
  const [languageFilter, setLanguageFilterState] = useState<string | null>(null);
  const [genderFilter, setGenderFilterState] = useState<"man" | "woman" | null>(null);
  const [hasBgmFilter, setHasBgmFilterState] = useState<boolean | null>(null);

  const loadPresets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listPresetVoices({
        language: languageFilter || undefined,
        gender: genderFilter || undefined,
        has_bgm: hasBgmFilter !== null ? hasBgmFilter : undefined,
        offset,
        limit,
      });
      setPresets(response.presets);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load presets");
    } finally {
      setLoading(false);
    }
  }, [languageFilter, genderFilter, hasBgmFilter, offset, limit]);

  const loadLanguages = useCallback(async () => {
    try {
      const response = await api.listPresetLanguages();
      setLanguages(response.languages);
    } catch (err) {
      console.error("Failed to load languages:", err);
    }
  }, []);

  const setPage = useCallback((page: number) => {
    setOffset(page * limit);
  }, [limit]);

  const setLimit = useCallback((newLimit: number) => {
    setLimitState(newLimit);
    setOffset(0); // Reset to first page
  }, []);

  const setLanguageFilter = useCallback((language: string | null) => {
    setLanguageFilterState(language);
    setOffset(0); // Reset to first page
  }, []);

  const setGenderFilter = useCallback((gender: "man" | "woman" | null) => {
    setGenderFilterState(gender);
    setOffset(0); // Reset to first page
  }, []);

  const setHasBgmFilter = useCallback((hasBgm: boolean | null) => {
    setHasBgmFilterState(hasBgm);
    setOffset(0); // Reset to first page
  }, []);

  const createPreset = useCallback(async (data: {
    name: string;
    language: string;
    gender: "man" | "woman";
    has_bgm: boolean;
    voice_file: File;
  }) => {
    const preset = await api.createPresetVoice(data);
    // Reload presets to get updated list
    await loadPresets();
    await loadLanguages();
    return preset;
  }, [loadPresets, loadLanguages]);

  const deletePreset = useCallback(async (filename: string) => {
    try {
      await api.deletePresetVoice(filename);
      // Reload presets
      await loadPresets();
      await loadLanguages();
      return true;
    } catch {
      return false;
    }
  }, [loadPresets, loadLanguages]);

  const batchDeletePresets = useCallback(async (filenames: string[]) => {
    const response = await api.batchDeletePresetVoices(filenames);
    // Reload presets
    await loadPresets();
    await loadLanguages();
    return {
      deleted: response.deleted,
      failed: response.failed,
    };
  }, [loadPresets, loadLanguages]);

  const refresh = useCallback(async () => {
    await Promise.all([loadPresets(), loadLanguages()]);
  }, [loadPresets, loadLanguages]);

  const value: PresetVoiceContextType = {
    presets,
    total,
    loading,
    error,
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
    refresh,
  };

  return (
    <PresetVoiceContext.Provider value={value}>
      {children}
    </PresetVoiceContext.Provider>
  );
}

export function usePresetVoice() {
  const context = useContext(PresetVoiceContext);
  if (context === undefined) {
    throw new Error("usePresetVoice must be used within a PresetVoiceProvider");
  }
  return context;
}
