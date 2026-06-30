import { useEffect, useMemo } from 'react'
import type { ModelItem, SizePreset } from '../../api/types'

interface ModelDropdownProps {
  models: ModelItem[]
  value: string
  onChange: (modelId: string) => void
  onRefresh: () => void
  refreshing?: boolean
  disabled?: boolean
}

function groupModels(models: ModelItem[]) {
  return {
    catalog: models.filter((m) => m.source === 'catalog'),
    local: models.filter((m) => m.source === 'local'),
  }
}

export function ModelDropdown({
  models,
  value,
  onChange,
  onRefresh,
  refreshing = false,
  disabled = false,
}: ModelDropdownProps) {
  const groups = useMemo(() => groupModels(models), [models])

  return (
    <div className="model-dropdown-row">
      <label className="field">
        <span className="field-label">Model</span>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled || models.length === 0}
          className="select"
        >
          <option value="">Select a model…</option>
          {groups.catalog.length > 0 && (
            <optgroup label="Catalog">
              {groups.catalog.map((model) => (
                <option
                  key={model.id}
                  value={model.id}
                  disabled={!model.compatible}
                  title={model.disabled_reason ?? undefined}
                >
                  {model.label}
                  {model.status === 'download' ? ' — Download' : ''}
                  {!model.compatible ? ' — Incompatible' : ''}
                </option>
              ))}
            </optgroup>
          )}
          {groups.local.length > 0 && (
            <optgroup label="Local (manual)">
              {groups.local.map((model) => (
                <option
                  key={model.id}
                  value={model.id}
                  title={model.disabled_reason ?? undefined}
                >
                  {model.label}
                  {model.status === 'unknown' ? ' — Unknown VRAM' : ''}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </label>
      <button
        type="button"
        className="btn btn-secondary"
        onClick={onRefresh}
        disabled={refreshing || disabled}
        title="Scan models folder for manually added models"
      >
        {refreshing ? 'Scanning…' : 'Refresh'}
      </button>
    </div>
  )
}

interface SizePresetPickerProps {
  presets: SizePreset[]
  value: string
  onChange: (preset: SizePreset) => void
  disabled?: boolean
}

export function SizePresetPicker({
  presets,
  value,
  onChange,
  disabled = false,
}: SizePresetPickerProps) {
  const selected = presets.find((p) => p.id === value)

  const compatibility =
    selected?.compatible === false
      ? 'unsupported'
      : selected && selected.min_vram_gb >= 8
        ? 'warning'
        : 'compatible'

  if (presets.length === 0) return null

  return (
    <div className="size-preset-picker">
      <span className="field-label">Size preset</span>
      <div className="preset-grid" role="group" aria-label="Size presets">
        {presets.map((preset) => {
          const isDisabled = preset.compatible === false || disabled
          const isActive = preset.id === value
          return (
            <button
              key={preset.id}
              type="button"
              className={`preset-btn ${isActive ? 'active' : ''}`}
              disabled={isDisabled}
              title={preset.disabled_reason ?? undefined}
              onClick={() => onChange(preset)}
            >
              <span className="preset-label">{preset.label}</span>
              <span className="preset-size">
                {preset.width} × {preset.height}
              </span>
            </button>
          )
        })}
      </div>
      {selected && (
        <p className={`compat-badge compat-${compatibility}`}>
          {compatibility === 'compatible' && 'Compatible with your GPU'}
          {compatibility === 'warning' && 'May require memory optimizations'}
          {compatibility === 'unsupported' &&
            (selected.disabled_reason ?? 'Not supported on this GPU')}
        </p>
      )}
    </div>
  )
}

interface PromptEditorProps {
  prompt: string
  negativePrompt: string
  onPromptChange: (value: string) => void
  onNegativePromptChange: (value: string) => void
  disabled?: boolean
}

export function PromptEditor({
  prompt,
  negativePrompt,
  onPromptChange,
  onNegativePromptChange,
  disabled = false,
}: PromptEditorProps) {
  return (
    <div className="prompt-editor">
      <label className="field">
        <span className="field-label">Prompt</span>
        <textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          rows={5}
          placeholder="Describe the image you want to generate…"
          disabled={disabled}
          className="textarea"
        />
      </label>
      <label className="field">
        <span className="field-label">Negative prompt</span>
        <textarea
          value={negativePrompt}
          onChange={(e) => onNegativePromptChange(e.target.value)}
          rows={3}
          placeholder="What to avoid (optional)…"
          disabled={disabled}
          className="textarea"
        />
      </label>
    </div>
  )
}

interface PromptSourceTabsProps {
  active: 'templates' | 'saved'
  onChange: (tab: 'templates' | 'saved') => void
}

export function PromptSourceTabs({ active, onChange }: PromptSourceTabsProps) {
  return (
    <div className="tab-row" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={active === 'templates'}
        className={`tab-btn ${active === 'templates' ? 'active' : ''}`}
        onClick={() => onChange('templates')}
      >
        Templates
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={active === 'saved'}
        className={`tab-btn ${active === 'saved' ? 'active' : ''}`}
        onClick={() => onChange('saved')}
      >
        My prompts
      </button>
    </div>
  )
}

export function useCompatiblePresets(
  model: ModelItem | undefined,
  currentPresetId: string,
  onPresetChange: (preset: SizePreset) => void,
) {
  const presets = model?.size_presets ?? []

  useEffect(() => {
    if (presets.length === 0) return

    const current = presets.find((p) => p.id === currentPresetId)
    if (current && current.compatible !== false) return

    const compatible = presets.filter((p) => p.compatible !== false)
    const fallback =
      compatible.find((p) => p.is_default) ??
      compatible[compatible.length - 1] ??
      presets.find((p) => p.is_default) ??
      presets[0]

    if (fallback && fallback.id !== currentPresetId) {
      onPresetChange(fallback)
    }
  }, [model?.id, presets, currentPresetId, onPresetChange])
}
