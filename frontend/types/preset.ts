/**
 * Preset voice types for VibeVoice
 */

export interface PresetVoice {
  filename: string;
  language: string;
  name: string;
  gender: 'man' | 'woman';
  has_bgm: boolean;
  display_name: string;
}

export interface PresetLanguage {
  code: string;
  name: string;
  count: number;
}

export interface ListPresetsResponse {
  presets: PresetVoice[];
  count: number;
}

export interface ListPresetLanguagesResponse {
  languages: PresetLanguage[];
}
