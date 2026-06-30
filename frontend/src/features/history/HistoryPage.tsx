import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteJob, fetchJob, fetchJobs } from '../../api/jobs'
import type { Job } from '../../api/types'
import { PageHeader } from '../../components/PageHeader'
import { Card } from '../../components/Card'
import { StatusBadge } from '../../components/StatusBadge'
import { Spinner } from '../../components/Spinner'
import { useGenerateForm } from '../../context/GenerateFormContext'
import { Gallery, ImagePreviewModal } from '../generate/Gallery'
import type { JobImage } from '../../api/types'

const PAGE_SIZE = 20

export function HistoryPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [previewImage, setPreviewImage] = useState<JobImage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchJobs({ limit: PAGE_SIZE, offset })
      setJobs(res.jobs)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [offset])

  useEffect(() => {
    void loadJobs()
  }, [loadJobs])

  const openJob = async (jobId: string) => {
    try {
      const job = await fetchJob(jobId)
      setSelectedJob(job)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load job')
    }
  }

  const handleDelete = async (jobId: string, deleteFiles: boolean) => {
    try {
      await deleteJob(jobId, deleteFiles)
      setSelectedJob(null)
      void loadJobs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  if (loading && jobs.length === 0) {
    return <Spinner label="Loading job history…" />
  }

  return (
    <div className="history-page">
      <PageHeader
        title="History"
        description="Browse past generation jobs and re-use their settings."
      />

      {error && <div className="error-box">{error}</div>}

      <div className="history-layout">
        <Card className="history-list-card">
          {jobs.length === 0 ? (
            <p className="muted">No jobs yet. Generate your first image.</p>
          ) : (
            <ul className="history-list">
              {jobs.map((job) => (
                <li key={job.id}>
                  <button
                    type="button"
                    className={`history-row ${
                      selectedJob?.id === job.id ? 'active' : ''
                    }`}
                    onClick={() => void openJob(job.id)}
                  >
                    <div className="history-row-top">
                      <StatusBadge status={job.status} />
                      <time dateTime={job.created_at}>
                        {new Date(job.created_at).toLocaleString()}
                      </time>
                    </div>
                    <p className="history-prompt">{job.prompt}</p>
                    <div className="history-row-meta">
                      <span>{job.model_label ?? job.model_id}</span>
                      <span>
                        {job.width}×{job.height}
                      </span>
                      <span>
                        {job.completed_count}/{job.image_count} images
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="pagination">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
            >
              Previous
            </button>
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </Card>

        {selectedJob && (
          <JobDetailPanel
            job={selectedJob}
            onClose={() => setSelectedJob(null)}
            onDelete={handleDelete}
            onPreview={setPreviewImage}
          />
        )}
      </div>

      <ImagePreviewModal
        image={previewImage}
        onClose={() => setPreviewImage(null)}
      />
    </div>
  )
}

interface JobDetailPanelProps {
  job: Job
  onClose: () => void
  onDelete: (jobId: string, deleteFiles: boolean) => void
  onPreview: (image: JobImage) => void
}

function JobDetailPanel({
  job,
  onClose,
  onDelete,
  onPreview,
}: JobDetailPanelProps) {
  const navigate = useNavigate()
  const { loadFromJob } = useGenerateForm()

  const handleUseAgain = () => {
    loadFromJob(job)
    navigate('/')
  }

  return (
    <Card className="job-detail-card" title="Job detail">
      <button type="button" className="modal-close" onClick={onClose}>
        ×
      </button>

      <div className="job-detail-meta">
        <StatusBadge status={job.status} />
        <span>{new Date(job.created_at).toLocaleString()}</span>
      </div>

      <dl className="detail-list">
        <div>
          <dt>Model</dt>
          <dd>{job.model_label ?? job.model_id}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>
            {job.width} × {job.height} ({job.size_preset_id})
          </dd>
        </div>
        <div>
          <dt>Steps</dt>
          <dd>{job.steps}</dd>
        </div>
        <div>
          <dt>Seed</dt>
          <dd>{job.seed ?? 'Random'}</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd className="mono">{job.output_directory}</dd>
        </div>
      </dl>

      <div className="prompt-block">
        <h4>Prompt</h4>
        <p>{job.prompt}</p>
        {job.negative_prompt && (
          <>
            <h4>Negative prompt</h4>
            <p>{job.negative_prompt}</p>
          </>
        )}
      </div>

      {job.error_message && (
        <div className="error-box">{job.error_message}</div>
      )}

      {job.images && job.images.length > 0 && (
        <Gallery images={job.images} onPreview={onPreview} />
      )}

      <div className="job-detail-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleUseAgain}
        >
          Use again
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            if (
              confirm(
                'Also delete image files from disk? OK = delete files, Cancel = DB only',
              )
            ) {
              onDelete(job.id, true)
            } else {
              onDelete(job.id, false)
            }
          }}
        >
          Delete job
        </button>
      </div>
    </Card>
  )
}
