import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadModel, fetchModels, refreshModels } from '../../api/models'
import { cancelJob, createJob, fetchJob, fetchRecentImages } from '../../api/jobs'
import {
  createSavedPrompt,
  fetchSavedPrompts,
  fetchTemplates,
} from '../../api/prompts'
import { fetchSettings } from '../../api/jobs'
import type {
  Job,
  JobImage,
  JobSSEEvent,
  ModelItem,
  PromptTemplate,
  SavedPrompt,
  SizePreset,
} from '../../api/types'
import { PageHeader } from '../../components/PageHeader'
import { Card } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { useGenerateForm } from '../../context/GenerateFormContext'
import { usePreflight } from '../../hooks/usePreflight'
import { useJobSSE } from '../../hooks/useJobSSE'
import {
  Gallery,
  GenerationProgress,
  ImagePreviewModal,
} from './Gallery'
import {
  ModelDropdown,
  PromptEditor,
  PromptSourceTabs,
  SizePresetPicker,
  useCompatiblePresets,
} from './GenerateComponents'

export function GeneratePage() {
  const { form, updateForm } = useGenerateForm()
  const { canGenerate, ensureFresh } = usePreflight()

  const [models, setModels] = useState<ModelItem[]>([])
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [savedPrompts, setSavedPrompts] = useState<SavedPrompt[]>([])
  const [recentImages, setRecentImages] = useState<JobImage[]>([])
  const [outputDirectory, setOutputDirectory] = useState('')
  const [promptTab, setPromptTab] = useState<'templates' | 'saved'>('templates')
  const [activeJob, setActiveJob] = useState<Job | null>(null)
  const [galleryImages, setGalleryImages] = useState<JobImage[]>([])
  const [previewImage, setPreviewImage] = useState<JobImage | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshingModels, setRefreshingModels] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSaveDialog, setShowSaveDialog] = useState(false)

  const selectedModel = useMemo(
    () => models.find((m) => m.id === form.modelId),
    [models, form.modelId],
  )

  const handlePresetChange = useCallback(
    (preset: SizePreset) => {
      updateForm({
        sizePresetId: preset.id,
        width: preset.width,
        height: preset.height,
      })
    },
    [updateForm],
  )

  useCompatiblePresets(selectedModel, form.sizePresetId, handlePresetChange)

  const handleSSEEvent = useCallback(
    (event: JobSSEEvent) => {
      if (event.type === 'image_completed' && event.image) {
        setGalleryImages((prev) => [...prev, event.image!])
      }
      if (event.type === 'done' || event.type === 'failed') {
        void fetchJob(event.job_id).then(setActiveJob)
        setGenerating(false)
      }
    },
    [],
  )

  const { connected, lastEvent } = useJobSSE({
    jobId: activeJob?.id ?? null,
    enabled: !!activeJob && (activeJob.status === 'running' || activeJob.status === 'queued'),
    onEvent: handleSSEEvent,
  })

  const loadPageData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [modelsRes, templatesRes, savedRes, settings, recent] =
        await Promise.all([
          fetchModels(),
          fetchTemplates(),
          fetchSavedPrompts(),
          fetchSettings(),
          fetchRecentImages(12),
        ])

      setModels(modelsRes.models)
      setTemplates(templatesRes)
      setSavedPrompts(savedRes)
      setOutputDirectory(settings.output_directory)

      if (!form.modelId && settings.last_model_id) {
        updateForm({
          modelId: settings.last_model_id,
          sizePresetId: settings.last_size_preset_id ?? '',
          steps: settings.last_steps ?? form.steps,
        })
      } else if (!form.modelId && modelsRes.models.length > 0) {
        const firstCompatible =
          modelsRes.models.find((m) => m.compatible) ?? modelsRes.models[0]
        updateForm({ modelId: firstCompatible.id })
      }

      setRecentImages(
        recent.map((img) => ({
          id: img.id,
          job_id: img.job_id,
          index: img.index,
          seed: 0,
          file_path: '',
          thumb_path: img.thumb_url,
          status: 'completed',
          created_at: img.created_at,
        })),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load page data')
    } finally {
      setLoading(false)
    }
  }, [form.modelId, form.steps, updateForm])

  useEffect(() => {
    void loadPageData()
  }, [loadPageData])

  const handleRefreshModels = async () => {
    setRefreshingModels(true)
    try {
      const res = await refreshModels()
      setModels(res.models)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Model refresh failed')
    } finally {
      setRefreshingModels(false)
    }
  }

  const handleModelChange = async (modelId: string) => {
    updateForm({ modelId })
    const model = models.find((m) => m.id === modelId)
    if (model?.status === 'download') {
      try {
        setGenerating(true)
        const updated = await downloadModel(modelId)
        setModels((prev) =>
          prev.map((m) => (m.id === updated.id ? updated : m)),
        )
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Download failed')
      } finally {
        setGenerating(false)
      }
    }
  }

  const handleGenerate = async () => {
    setError(null)

    const preflight = await ensureFresh()
    if (!preflight?.critical_passed) {
      setError('Critical system checks failed. Open Settings to fix issues.')
      return
    }

    if (!form.prompt.trim()) {
      setError('Enter a prompt before generating.')
      return
    }
    if (!form.modelId || !form.sizePresetId) {
      setError('Select a model and size preset.')
      return
    }

    setGenerating(true)
    setGalleryImages([])

    try {
      const job = await createJob({
        prompt: form.prompt,
        negative_prompt: form.negativePrompt,
        model_id: form.modelId,
        size_preset_id: form.sizePresetId,
        width: form.width,
        height: form.height,
        steps: form.steps,
        seed: form.useRandomSeed ? null : form.seed,
        image_count: form.imageCount,
      })
      setActiveJob(job)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation')
      setGenerating(false)
    }
  }

  const handleCancel = async () => {
    if (!activeJob) return
    try {
      const job = await cancelJob(activeJob.id)
      setActiveJob(job)
      setGenerating(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    }
  }

  const loadTemplate = (template: PromptTemplate) => {
    updateForm({
      prompt: template.prompt,
      negativePrompt: template.negative_prompt,
      loadedPromptId: null,
    })
  }

  const loadSavedPrompt = (prompt: SavedPrompt) => {
    updateForm({
      prompt: prompt.prompt,
      negativePrompt: prompt.negative_prompt,
      loadedPromptId: prompt.id,
    })
  }

  if (loading) {
    return <Spinner label="Loading generate page…" />
  }

  return (
    <div className="generate-page">
      <PageHeader
        title="Generate"
        description="Create images locally with your selected model and prompts."
      />

      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}

      <div className="generate-layout">
        <div className="generate-main">
          <Card title="Prompt">
            <PromptSourceTabs active={promptTab} onChange={setPromptTab} />

            {promptTab === 'templates' && (
              <div className="prompt-picker">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    className="prompt-chip"
                    onClick={() => loadTemplate(template)}
                  >
                    {template.name}
                  </button>
                ))}
                {templates.length === 0 && (
                  <p className="muted">No bundled templates available.</p>
                )}
              </div>
            )}

            {promptTab === 'saved' && (
              <div className="prompt-picker">
                {savedPrompts.map((prompt) => (
                  <button
                    key={prompt.id}
                    type="button"
                    className="prompt-chip"
                    onClick={() => loadSavedPrompt(prompt)}
                  >
                    {prompt.is_favorite && '★ '}
                    {prompt.name}
                  </button>
                ))}
                {savedPrompts.length === 0 && (
                  <p className="muted">
                    No saved prompts yet.{' '}
                    <Link to="/prompts">Browse prompts</Link>
                  </p>
                )}
              </div>
            )}

            <PromptEditor
              prompt={form.prompt}
              negativePrompt={form.negativePrompt}
              onPromptChange={(prompt) => updateForm({ prompt })}
              onNegativePromptChange={(negativePrompt) =>
                updateForm({ negativePrompt })
              }
              disabled={generating}
            />

            <div className="prompt-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowSaveDialog(true)}
                disabled={!form.prompt.trim()}
              >
                Save to library
              </button>
              {form.loadedPromptId && (
                <Link
                  to="/prompts"
                  className="btn btn-ghost"
                  state={{ editId: form.loadedPromptId }}
                >
                  Update library entry
                </Link>
              )}
            </div>
          </Card>

          <Card title="Model & settings">
            <ModelDropdown
              models={models}
              value={form.modelId}
              onChange={handleModelChange}
              onRefresh={handleRefreshModels}
              refreshing={refreshingModels}
              disabled={generating}
            />

            {selectedModel && (
              <SizePresetPicker
                presets={selectedModel.size_presets ?? []}
                value={form.sizePresetId}
                onChange={handlePresetChange}
                disabled={generating}
              />
            )}

            <div className="settings-grid">
              <label className="field">
                <span className="field-label">Steps</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={form.steps}
                  onChange={(e) =>
                    updateForm({ steps: Number(e.target.value) })
                  }
                  disabled={generating}
                  className="input"
                />
              </label>

              <label className="field">
                <span className="field-label">Image count</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={form.imageCount}
                  onChange={(e) =>
                    updateForm({ imageCount: Number(e.target.value) })
                  }
                  disabled={generating}
                  className="input"
                />
              </label>

              <label className="field checkbox-field">
                <input
                  type="checkbox"
                  checked={form.useRandomSeed}
                  onChange={(e) =>
                    updateForm({ useRandomSeed: e.target.checked })
                  }
                  disabled={generating}
                />
                <span>Random seed</span>
              </label>

              {!form.useRandomSeed && (
                <label className="field">
                  <span className="field-label">Seed</span>
                  <input
                    type="number"
                    value={form.seed ?? ''}
                    onChange={(e) =>
                      updateForm({
                        seed: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    disabled={generating}
                    className="input"
                  />
                </label>
              )}
            </div>

            <p className="output-path muted">
              Output: {outputDirectory || 'Not configured'}{' '}
              <Link to="/settings">Change in Settings</Link>
            </p>
          </Card>

          <div className="generate-actions">
            <button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={handleGenerate}
              disabled={!canGenerate || generating || !form.prompt.trim()}
            >
              {generating ? 'Generating…' : 'Generate'}
            </button>
          </div>

          <GenerationProgress
            job={activeJob}
            lastEvent={lastEvent}
            connected={connected}
            onCancel={handleCancel}
            onRetrySmaller={(presetId) =>
              updateForm({ sizePresetId: presetId })
            }
          />
        </div>

        <aside className="generate-sidebar">
          <Card title="Gallery">
            <Gallery
              images={
                galleryImages.length > 0 ? galleryImages : recentImages
              }
              onPreview={setPreviewImage}
            />
          </Card>
        </aside>
      </div>

      {showSaveDialog && (
        <SavePromptDialog
          prompt={form.prompt}
          negativePrompt={form.negativePrompt}
          onClose={() => setShowSaveDialog(false)}
          onSaved={(saved) => {
            setSavedPrompts((prev) => [saved, ...prev])
            updateForm({ loadedPromptId: saved.id })
            setShowSaveDialog(false)
          }}
        />
      )}

      <ImagePreviewModal
        image={previewImage}
        onClose={() => setPreviewImage(null)}
      />
    </div>
  )
}

interface SavePromptDialogProps {
  prompt: string
  negativePrompt: string
  onClose: () => void
  onSaved: (prompt: SavedPrompt) => void
}

function SavePromptDialog({
  prompt,
  negativePrompt,
  onClose,
  onSaved,
}: SavePromptDialogProps) {
  const [name, setName] = useState('')
  const [tags, setTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    setSaving(true)
    try {
      const saved = await createSavedPrompt({
        name: name.trim(),
        prompt,
        negative_prompt: negativePrompt,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      })
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal
        aria-label="Save prompt"
      >
        <h3>Save to library</h3>
        {error && <p className="error-text">{error}</p>}
        <label className="field">
          <span className="field-label">Name</span>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </label>
        <label className="field">
          <span className="field-label">Tags (comma-separated)</span>
          <input
            className="input"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </label>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
