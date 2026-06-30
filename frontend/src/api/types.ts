export type ModelSource = 'catalog' | 'local'
export type ModelStatus = 'ready' | 'download' | 'unknown'
export type JobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'interrupted'
export type PreflightStatus = 'pass' | 'warn' | 'fail'
export type PreflightSeverity = 'critical' | 'warning' | 'info'
export type CompatibilityLevel = 'compatible' | 'warning' | 'unsupported'

export interface SizePreset {
  id: string
  width: number
  height: number
  label: string
  min_vram_gb: number
  is_default: boolean
  compatible?: boolean
  disabled_reason?: string | null
}

export interface ModelItem {
  id: string
  label: string
  source: ModelSource
  status: ModelStatus
  compatible: boolean
  family: string
  disabled_reason?: string | null
  size_presets?: SizePreset[]
}

export interface ModelsResponse {
  models: ModelItem[]
  total_vram_gb?: number
}

export interface PromptTemplate {
  id: string
  name: string
  prompt: string
  negative_prompt: string
  description?: string
}

export interface SavedPrompt {
  id: string
  name: string
  prompt: string
  negative_prompt: string
  tags: string[]
  is_favorite: boolean
  source_template_id?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CreateSavedPromptInput {
  name: string
  prompt: string
  negative_prompt?: string
  tags?: string[]
  is_favorite?: boolean
  source_template_id?: string | null
  notes?: string | null
}

export interface AppSettings {
  output_directory: string
  last_model_id?: string | null
  last_size_preset_id?: string | null
  last_steps?: number
  history_retention_days?: number
  history_retention_max_jobs?: number
  log_retention_days?: number
}

export interface PreflightItem {
  id: string
  name: string
  status: PreflightStatus
  severity: PreflightSeverity
  message: string
  fix_hint?: string | null
}

export interface PreflightResult {
  ready: boolean
  critical_passed: boolean
  warning_count: number
  checked_at: string
  items: PreflightItem[]
  gpu_name?: string | null
  driver_version?: string | null
  total_vram_mb?: number | null
  free_vram_mb?: number | null
}

export interface JobImage {
  id: string
  job_id: string
  index: number
  seed: number
  file_path: string
  thumb_path?: string | null
  status: 'completed' | 'failed' | 'file_missing'
  created_at: string
}

export interface Job {
  id: string
  status: JobStatus
  prompt: string
  negative_prompt: string
  model_id: string
  model_label?: string
  size_preset_id: string
  width: number
  height: number
  steps: number
  seed?: number | null
  image_count: number
  completed_count: number
  error_message?: string | null
  output_directory: string
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  images?: JobImage[]
}

export interface CreateJobInput {
  prompt: string
  negative_prompt?: string
  model_id: string
  size_preset_id: string
  width: number
  height: number
  steps: number
  seed?: number | null
  image_count: number
}

export interface JobsListResponse {
  jobs: Job[]
  total: number
}

export interface RecentImage {
  id: string
  job_id: string
  index: number
  thumb_url: string
  created_at: string
}

export type JobSSEEventType =
  | 'step'
  | 'progress'
  | 'image_completed'
  | 'failed'
  | 'done'
  | 'cancelled'

export interface JobSSEEvent {
  type: JobSSEEventType
  job_id: string
  step?: number
  total_steps?: number
  image_index?: number
  image?: JobImage
  progress?: number
  error?: string
  suggested_preset_id?: string | null
}

export interface GenerateFormState {
  prompt: string
  negativePrompt: string
  modelId: string
  sizePresetId: string
  width: number
  height: number
  steps: number
  seed: number | null
  useRandomSeed: boolean
  imageCount: number
  loadedPromptId: string | null
}

export const DEFAULT_STEPS = 25
export const DEFAULT_IMAGE_COUNT = 1

export function createDefaultFormState(): GenerateFormState {
  return {
    prompt: '',
    negativePrompt: '',
    modelId: '',
    sizePresetId: '',
    width: 512,
    height: 512,
    steps: DEFAULT_STEPS,
    seed: null,
    useRandomSeed: true,
    imageCount: DEFAULT_IMAGE_COUNT,
    loadedPromptId: null,
  }
}
