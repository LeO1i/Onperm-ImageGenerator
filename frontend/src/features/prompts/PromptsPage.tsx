import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  createSavedPrompt,
  deleteSavedPrompt,
  fetchSavedPrompts,
  updateSavedPrompt,
} from '../../api/prompts'
import type { SavedPrompt } from '../../api/types'
import { PageHeader } from '../../components/PageHeader'
import { Card } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { useGenerateForm } from '../../context/GenerateFormContext'

export function PromptsPage() {
  const [prompts, setPrompts] = useState<SavedPrompt[]>([])
  const [search, setSearch] = useState('')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [tagFilter, setTagFilter] = useState('')
  const [editing, setEditing] = useState<SavedPrompt | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const { updateForm } = useGenerateForm()

  const loadPrompts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSavedPrompts({
        q: search || undefined,
        tag: tagFilter || undefined,
        favorite: favoritesOnly || undefined,
      })
      setPrompts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompts')
    } finally {
      setLoading(false)
    }
  }, [search, tagFilter, favoritesOnly])

  useEffect(() => {
    void loadPrompts()
  }, [loadPrompts])

  useEffect(() => {
    const editId = (location.state as { editId?: string } | null)?.editId
    if (!editId) return
    void fetchSavedPrompts().then((all) => {
      const found = all.find((p) => p.id === editId)
      if (found) setEditing(found)
    })
    navigate(location.pathname, { replace: true, state: null })
  }, [location, navigate])

  const allTags = useMemo(() => {
    const tags = new Set<string>()
    prompts.forEach((p) => p.tags.forEach((t) => tags.add(t)))
    return Array.from(tags).sort()
  }, [prompts])

  const handleLoad = (prompt: SavedPrompt) => {
    updateForm({
      prompt: prompt.prompt,
      negativePrompt: prompt.negative_prompt,
      loadedPromptId: prompt.id,
    })
    navigate('/')
  }

  const handleToggleFavorite = async (prompt: SavedPrompt) => {
    try {
      const updated = await updateSavedPrompt(prompt.id, {
        is_favorite: !prompt.is_favorite,
      })
      setPrompts((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  const handleDuplicate = async (prompt: SavedPrompt) => {
    try {
      const copy = await createSavedPrompt({
        name: `${prompt.name} (copy)`,
        prompt: prompt.prompt,
        negative_prompt: prompt.negative_prompt,
        tags: prompt.tags,
      })
      setPrompts((prev) => [copy, ...prev])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Duplicate failed')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this saved prompt?')) return
    try {
      await deleteSavedPrompt(id)
      setPrompts((prev) => prev.filter((p) => p.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <div className="prompts-page">
      <PageHeader
        title="Prompt library"
        description="Search, favorite, and reuse your saved prompts."
      />

      {error && <div className="error-box">{error}</div>}

      <Card>
        <div className="prompts-filters">
          <input
            className="input"
            placeholder="Search prompts…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="select"
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
          >
            <option value="">All tags</option>
            {allTags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={favoritesOnly}
              onChange={(e) => setFavoritesOnly(e.target.checked)}
            />
            <span>Favorites only</span>
          </label>
        </div>

        {loading ? (
          <Spinner label="Loading prompts…" small />
        ) : prompts.length === 0 ? (
          <p className="muted">No saved prompts match your filters.</p>
        ) : (
          <ul className="prompts-list">
            {prompts.map((prompt) => (
              <li key={prompt.id} className="prompts-list-item">
                <div className="prompts-list-main">
                  <button
                    type="button"
                    className={`favorite-btn ${prompt.is_favorite ? 'active' : ''}`}
                    onClick={() => void handleToggleFavorite(prompt)}
                    aria-label="Toggle favorite"
                  >
                    ★
                  </button>
                  <div>
                    <h3>{prompt.name}</h3>
                    <p className="prompt-preview">{prompt.prompt}</p>
                    {prompt.tags.length > 0 && (
                      <div className="tag-row">
                        {prompt.tags.map((tag) => (
                          <span key={tag} className="tag">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="prompts-list-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => handleLoad(prompt)}
                  >
                    Load
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setEditing(prompt)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => void handleDuplicate(prompt)}
                  >
                    Duplicate
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => void handleDelete(prompt.id)}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {editing && (
        <EditPromptDialog
          prompt={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setPrompts((prev) =>
              prev.map((p) => (p.id === updated.id ? updated : p)),
            )
            setEditing(null)
          }}
        />
      )}
    </div>
  )
}

interface EditPromptDialogProps {
  prompt: SavedPrompt
  onClose: () => void
  onSaved: (prompt: SavedPrompt) => void
}

function EditPromptDialog({ prompt, onClose, onSaved }: EditPromptDialogProps) {
  const [name, setName] = useState(prompt.name)
  const [text, setText] = useState(prompt.prompt)
  const [negative, setNegative] = useState(prompt.negative_prompt)
  const [tags, setTags] = useState(prompt.tags.join(', '))
  const [notes, setNotes] = useState(prompt.notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await updateSavedPrompt(prompt.id, {
        name: name.trim(),
        prompt: text,
        negative_prompt: negative,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        notes: notes || undefined,
      })
      onSaved(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-content modal-lg"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal
      >
        <h3>Edit prompt</h3>
        {error && <p className="error-text">{error}</p>}
        <label className="field">
          <span className="field-label">Name</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Prompt</span>
          <textarea className="textarea" rows={4} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Negative prompt</span>
          <textarea className="textarea" rows={3} value={negative} onChange={(e) => setNegative(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Tags</span>
          <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Notes</span>
          <textarea className="textarea" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
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
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
