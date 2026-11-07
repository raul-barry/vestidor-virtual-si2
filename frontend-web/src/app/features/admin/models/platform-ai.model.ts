export interface PlatformAIConfig {
  configured: boolean;
  masked_api_key: string | null;
  primary_model: string;
  fast_model: string;
  vision_model: string;
  transcription_model: string;
  capability_models?: Record<string, string>;
  experimental_models: string[];
  last_test_status: string | null;
  last_test_at: string | null;
}

export interface PlatformAIModel {
  id: string;
  active: boolean;
  experimental: boolean;
  capabilities: string[];
}

export interface PlatformAIConfigUpdate {
  api_key?: string;
  primary_model: string;
  fast_model: string;
  vision_model: string;
  transcription_model: string;
  capability_models?: Record<string, string>;
}

export const PLATFORM_AI_CAPABILITIES = [
  { key: 'general_chat', label: 'Asistente general', type: 'text' },
  { key: 'complex_reasoning', label: 'Razonamiento complejo', type: 'text' },
  { key: 'business_reports', label: 'Reportes empresariales', type: 'text' },
  { key: 'sales_analysis', label: 'Análisis de ventas', type: 'text' },
  { key: 'recommendations', label: 'Recomendaciones empresariales', type: 'text' },
  { key: 'uml_assistant', label: 'Asistente UML', type: 'text' },
  { key: 'image_understanding', label: 'Interpretación de imágenes', type: 'vision' },
  { key: 'speech_transcription', label: 'Transcripción de voz', type: 'transcription' },
] as const;

export const DEFAULT_PLATFORM_AI_CAPABILITIES: Record<string, string> = {
  general_chat: 'openai/gpt-oss-20b', complex_reasoning: 'openai/gpt-oss-120b',
  business_reports: 'openai/gpt-oss-120b', sales_analysis: 'openai/gpt-oss-120b',
  recommendations: 'openai/gpt-oss-120b', uml_assistant: 'openai/gpt-oss-120b',
  image_understanding: 'qwen/qwen3.8-27b', speech_transcription: 'whisper-large-v3-turbo',
};
