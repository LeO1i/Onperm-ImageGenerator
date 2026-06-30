import type { Job, JobImage, JobSSEEvent } from '../../api/types'

interface GenerationProgressProps {
  job: Job | null
  lastEvent: JobSSEEvent | null
  connected: boolean
  onCancel?: () => void
  onRetrySmaller?: (presetId: string) => void
}

export function GenerationProgress({
  job,
  lastEvent,
  connected,
  onCancel,
  onRetrySmaller,
}: GenerationProgressProps) {
  if (!job) return null

  const step = lastEvent?.step ?? 0
  const totalSteps = lastEvent?.total_steps ?? job.steps
  const progress =
    lastEvent?.progress ??
    (job.status === 'completed'
      ? 100
      : Math.round((job.completed_count / job.image_count) * 100))

  const isActive = job.status === 'running' || job.status === 'queued'

  return (
    <div className="generation-progress card">
      <div className="progress-header">
        <h3>Generation progress</h3>
        <span className={`sse-status ${connected ? 'connected' : ''}`}>
          {connected ? 'Live' : 'Reconnecting…'}
        </span>
      </div>

      <div className="progress-meta">
        <span>Status: {job.status}</span>
        <span>
          Images: {job.completed_count} / {job.image_count}
        </span>
        {isActive && totalSteps > 0 && (
          <span>
            Step: {step} / {totalSteps}
          </span>
        )}
      </div>

      <div className="progress-bar" aria-hidden>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {job.error_message && (
        <div className="error-box" role="alert">
          <p>{job.error_message}</p>
          {lastEvent?.suggested_preset_id && onRetrySmaller && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onRetrySmaller(lastEvent.suggested_preset_id!)}
            >
              Retry with smaller size
            </button>
          )}
        </div>
      )}

      {isActive && onCancel && (
        <button type="button" className="btn btn-danger" onClick={onCancel}>
          Cancel job
        </button>
      )}
    </div>
  )
}

interface GalleryProps {
  images: JobImage[]
  onPreview?: (image: JobImage) => void
}

export function Gallery({ images, onPreview }: GalleryProps) {
  if (images.length === 0) {
    return (
      <div className="gallery-empty">
        <p>Generated images will appear here.</p>
      </div>
    )
  }

  return (
    <div className="gallery-grid">
      {images.map((image) => {
        const thumbUrl = image.thumb_path
          ? `/api/thumbs/${encodeURIComponent(image.id)}`
          : null

        return (
          <button
            key={image.id}
            type="button"
            className="gallery-item"
            onClick={() => onPreview?.(image)}
            disabled={image.status === 'file_missing'}
          >
            {thumbUrl ? (
              <img src={thumbUrl} alt={`Generated image ${image.index}`} />
            ) : (
              <div className="gallery-placeholder">#{image.index}</div>
            )}
            <span className="gallery-meta">Seed {image.seed}</span>
            {image.status === 'file_missing' && (
              <span className="gallery-missing">File missing</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

interface ImagePreviewModalProps {
  image: JobImage | null
  onClose: () => void
}

export function ImagePreviewModal({ image, onClose }: ImagePreviewModalProps) {
  if (!image) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-content image-preview-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal
        aria-label="Image preview"
      >
        <button type="button" className="modal-close" onClick={onClose}>
          ×
        </button>
        <img
          src={`/api/images/${encodeURIComponent(image.id)}`}
          alt={`Full size image ${image.index}`}
        />
        <div className="preview-actions">
          <a
            className="btn btn-secondary"
            href={`/api/images/${encodeURIComponent(image.id)}?download=1`}
            download
          >
            Download
          </a>
          <span className="preview-meta">Seed {image.seed}</span>
        </div>
      </div>
    </div>
  )
}
