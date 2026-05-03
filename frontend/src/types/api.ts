export interface IndexedFile {
  source_file: string;
  file_name: string;
  doc_type: string;
  file_md5: string;
  chunk_count: number;
  created_date: string | null;
  import_date: string | null;
  duplicate_with: string | null;
}

export interface KBStats {
  total_files: number;
  type_distribution: Record<string, number>;
  last_updated: string | null;
}

export type SourceType = "local" | "online";

export interface UnifiedSearchResult {
  source_type: SourceType;
  title: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SourceAttribution {
  title: string;
  source_type: SourceType;
  url: string | null;
  date: string | null;
}

export interface GenerationResult {
  content: string;
  sources: SourceAttribution[];
  output_path: string | null;
  template_used: string;
}

export interface TemplateSection {
  title: string;
  writing_points: string[];
  format_rules: string[];
}

export interface TemplateDef {
  id: string;
  name: string;
  doc_type: string;
  sections: TemplateSection[];
  is_builtin: boolean;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  local_only?: boolean;
}

export interface SelectedRefContent {
  title: string;
  content: string;
}

export interface GenerationRequest {
  description: string;
  selected_refs?: string[] | null;
  selected_ref_contents?: SelectedRefContent[] | null;
  requirements?: string | null;
  template_id?: string | null;
}

export interface FileListParams {
  doc_types?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: "file_name" | "import_date" | "chunk_count";
  sort_order?: "asc" | "desc";
}

export interface TaskProgress {
  task_id: string;
  status: "pending" | "running" | "completed" | "cancelled" | "failed";
  total: number;
  processed: number;
  success: number;
  failed: number;
  skipped: number;
  failed_files: { path: string; status: string; error: string | null }[];
  pending_files: string[];
  created_at: string;
  updated_at: string;
}

export interface KBSettings {
  source_folder: string;
  db_path: string;
  chunk_size: number;
  chunk_overlap: number;
}

export interface KBSettingsUpdate {
  source_folder?: string | null;
  db_path?: string | null;
  chunk_size?: number | null;
  chunk_overlap?: number | null;
}

export interface LLMSettings {
  default_provider: string;
  embed_provider: string;
  ollama_base_url: string;
  ollama_chat_model: string;
  ollama_embed_model: string;
  claude_base_url: string;
  claude_api_key: string;
  claude_chat_model: string;
  openai_base_url: string;
  openai_api_key: string;
  openai_chat_model: string;
  openai_embed_model: string;
}

export interface LLMSettingsUpdate {
  default_provider?: string | null;
  embed_provider?: string | null;
  ollama_base_url?: string | null;
  ollama_chat_model?: string | null;
  ollama_embed_model?: string | null;
  claude_base_url?: string | null;
  claude_api_key?: string | null;
  claude_chat_model?: string | null;
  openai_base_url?: string | null;
  openai_api_key?: string | null;
  openai_chat_model?: string | null;
  openai_embed_model?: string | null;
}

export interface GenerationSettings {
  output_format: string;
  save_path: string;
  include_sources: boolean;
  word_template_path: string;
}

export interface GenerationSettingsUpdate {
  output_format?: string | null;
  save_path?: string | null;
  include_sources?: boolean | null;
  word_template_path?: string | null;
}

export interface OnlineSearchConfig {
  enabled: boolean;
  provider: string;
  api_key: string;
  base_url: string;
  domains: string[];
  max_results: number;
}

export interface OnlineSearchConfigUpdate {
  enabled?: boolean | null;
  provider?: string | null;
  api_key?: string | null;
  base_url?: string | null;
  domains?: string[] | null;
  max_results?: number | null;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
}

export interface BrowseResult {
  path: string;
  children: { name: string; path: string; is_dir: boolean }[];
}

export interface PptxRequest {
  source_type: "upload" | "kb" | "session";
  file_path?: string;
  template_path?: string;
}

export interface SlideContent {
  slide_type: "cover" | "toc" | "chapter" | "conclusion";
  title: string;
  bullets: string[];
}

export interface PptxResult {
  status: string;
  current_step: string;
  step_index: number;
  total_steps: number;
  output_path: string | null;
  slide_count: number;
  slides: SlideContent[];
  source_doc: string;
  duration_ms: number;
  download_url: string | null;
  error: string | null;
}
