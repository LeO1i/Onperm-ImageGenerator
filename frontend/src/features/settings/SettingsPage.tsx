import { useCallback, useEffect, useState } from 'react'
import {
  browseOutputDirectory,
  fetchSettings,
  updateSettings,
  validateOutputDirectory,
} from '../../api/jobs'
import { rerunPreflight } from '../../api/system'
import type { AppSettings, PreflightResult } from '../../api/types'
import { PageHeader } from '../../components/PageHeader'
import { Card } from '../../components/Card'
import { StatusBadge } from '../../components/StatusBadge'
import { Spinner } from '../../components/Spinner'
import { usePreflight } from '../../hooks/usePreflight'

export function SettingsPage() {
  const { preflight, loading: preflightLoading, rerun } = usePreflight()
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [outputPath, setOutputPath] = useState('')
  const [historyDays, setHistoryDays] = useState(90)
  const [historyMaxJobs, setHistoryMaxJobs] = useState(500)
  const [logDays, setLogDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [systemStatus, setSystemStatus] = useState<PreflightResult | null>(null)
  const [rerunning, setRerunning] = useState(false)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSettings()
      setSettings(data)
      setOutputPath(data.output_directory)
      setHistoryDays(data.history_retention_days ?? 90)
      setHistoryMaxJobs(data.history_retention_max_jobs ?? 500)
      setLogDays(data.log_retention_days ?? 30)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadSettings()
  }, [loadSettings])

  useEffect(() => {
    setSystemStatus(preflight)
  }, [preflight])

  const handleValidatePath = async () => {
    setMessage(null)
    setError(null)
    try {
      const result = await validateOutputDirectory(outputPath)
      if (result.valid) {
        setMessage('Path is valid and writable.')
      } else {
        setError(result.message ?? 'Path is not valid.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed')
    }
  }

  const handleBrowse = async () => {
    try {
      const result = await browseOutputDirectory()
      if (result.path) setOutputPath(result.path)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Browse failed')
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const updated = await updateSettings({
        output_directory: outputPath,
        history_retention_days: historyDays,
        history_retention_max_jobs: historyMaxJobs,
        log_retention_days: logDays,
      })
      setSettings(updated)
      setMessage('Settings saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleRerunChecks = async () => {
    setRerunning(true)
    try {
      const result = await rerunPreflight()
      setSystemStatus(result)
      rerun()
      setMessage('System checks completed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Checks failed')
    } finally {
      setRerunning(false)
    }
  }

  if (loading) {
    return <Spinner label="Loading settings…" />
  }

  return (
    <div className="settings-page">
      <PageHeader
        title="Settings"
        description="Configure output paths, retention, and review system status."
      />

      {message && <div className="success-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <div className="settings-grid-layout">
        <Card title="Output directory">
          <label className="field">
            <span className="field-label">Save images to</span>
            <input
              className="input mono"
              value={outputPath}
              onChange={(e) => setOutputPath(e.target.value)}
            />
          </label>
          <div className="button-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleBrowse}
            >
              Browse…
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleValidatePath}
            >
              Validate
            </button>
          </div>
          {settings?.output_directory && (
            <p className="muted">Current: {settings.output_directory}</p>
          )}
        </Card>

        <Card title="Retention">
          <label className="field">
            <span className="field-label">History retention (days)</span>
            <input
              type="number"
              className="input"
              min={1}
              value={historyDays}
              onChange={(e) => setHistoryDays(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span className="field-label">Max jobs to keep</span>
            <input
              type="number"
              className="input"
              min={1}
              value={historyMaxJobs}
              onChange={(e) => setHistoryMaxJobs(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span className="field-label">Log retention (days)</span>
            <input
              type="number"
              className="input"
              min={1}
              value={logDays}
              onChange={(e) => setLogDays(Number(e.target.value))}
            />
          </label>
        </Card>

        <Card title="System status">
          {preflightLoading && !systemStatus ? (
            <Spinner label="Loading checks…" small />
          ) : systemStatus ? (
            <SystemStatusPanel
              result={systemStatus}
              onRerun={handleRerunChecks}
              rerunning={rerunning}
            />
          ) : (
            <p className="muted">System status unavailable.</p>
          )}
        </Card>
      </div>

      <div className="settings-footer">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Save settings'}
        </button>
      </div>
    </div>
  )
}

interface SystemStatusPanelProps {
  result: PreflightResult
  onRerun: () => void
  rerunning: boolean
}

function SystemStatusPanel({
  result,
  onRerun,
  rerunning,
}: SystemStatusPanelProps) {
  return (
    <div className="system-status">
      <div className="system-summary">
        <p>
          Critical checks:{' '}
          <strong>{result.critical_passed ? 'Passed' : 'Failed'}</strong>
        </p>
        <p>Warnings: {result.warning_count}</p>
        <p className="muted">
          Last checked: {new Date(result.checked_at).toLocaleString()}
        </p>
        {(result.gpu_name || result.total_vram_mb) && (
          <div className="gpu-summary">
            {result.gpu_name && <p>GPU: {result.gpu_name}</p>}
            {result.driver_version && (
              <p>Driver: {result.driver_version}</p>
            )}
            {result.total_vram_mb != null && (
              <p>VRAM: {Math.round(result.total_vram_mb / 1024)} GB total</p>
            )}
            {result.free_vram_mb != null && (
              <p>{Math.round(result.free_vram_mb / 1024)} GB free now</p>
            )}
          </div>
        )}
      </div>

      <button
        type="button"
        className="btn btn-secondary"
        onClick={onRerun}
        disabled={rerunning}
      >
        {rerunning ? 'Running checks…' : 'Re-run checks'}
      </button>

      <ul className="checklist">
        {result.items.map((item) => (
          <li key={item.id} className={`check-item check-${item.status}`}>
            <div className="check-item-header">
              <StatusBadge status={item.status} />
              <strong>{item.name}</strong>
              <span className="severity">{item.severity}</span>
            </div>
            <p>{item.message}</p>
            {item.fix_hint && <p className="fix-hint">{item.fix_hint}</p>}
          </li>
        ))}
      </ul>
    </div>
  )
}
