/**
 * Preset voice types for VibeVoice
 *
 * Preset voices use filename-based metadata.
 * Filename convention: {language}-{name}_{gender}[_bgm].wav
 * Examples:
 *   - en-Alice_woman.wav
 *   - zh-Bowen_man.wav
 *   - en-Mary_woman_bgm.wav
 */

export interface PresetVoice {
  filename: string;       // e.g., "en-Alice_woman.wav"
  language: string;       // e.g., "en", "zh", "in"
  name: string;           // e.g., "Alice"
  gender: "man" | "woman";
  has_bgm: boolean;
  display_name: string;   // e.g., "Alice (English, Female)"
}

export interface PresetLanguage {
  code: string;
  name: string;
  count: number;
}

export interface ListPresetsResponse {
  presets: PresetVoice[];
  count: number;
  total: number;
  offset: number;
  limit: number | null;
}

export interface ListPresetLanguagesResponse {
  languages: PresetLanguage[];
}

export interface CreatePresetRequest {
  name: string;
  language: string;
  gender: "man" | "woman";
  has_bgm: boolean;
  voice_file: File;
}

export interface DeletePresetResponse {
  message: string;
  filename: string;
}

export interface BatchDeletePresetsResponse {
  message: string;
  deleted_count: number;
  failed_count: number;
  deleted: string[];  // filenames
  failed: string[];   // filenames
}
