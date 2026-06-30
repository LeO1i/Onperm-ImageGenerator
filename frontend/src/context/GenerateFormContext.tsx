import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  createDefaultFormState,
  type GenerateFormState,
  type Job,
} from '../api/types'

interface GenerateFormContextValue {
  form: GenerateFormState
  setForm: React.Dispatch<React.SetStateAction<GenerateFormState>>
  updateForm: (patch: Partial<GenerateFormState>) => void
  loadFromJob: (job: Job) => void
  resetForm: () => void
}

const GenerateFormContext = createContext<GenerateFormContextValue | null>(null)

export function GenerateFormProvider({ children }: { children: ReactNode }) {
  const [form, setForm] = useState<GenerateFormState>(createDefaultFormState)

  const updateForm = useCallback((patch: Partial<GenerateFormState>) => {
    setForm((prev) => ({ ...prev, ...patch }))
  }, [])

  const loadFromJob = useCallback((job: Job) => {
    setForm({
      prompt: job.prompt,
      negativePrompt: job.negative_prompt,
      modelId: job.model_id,
      sizePresetId: job.size_preset_id,
      width: job.width,
      height: job.height,
      steps: job.steps,
      seed: job.seed ?? null,
      useRandomSeed: job.seed == null,
      imageCount: job.image_count,
      loadedPromptId: null,
    })
  }, [])

  const resetForm = useCallback(() => {
    setForm(createDefaultFormState())
  }, [])

  const value = useMemo(
    () => ({ form, setForm, updateForm, loadFromJob, resetForm }),
    [form, updateForm, loadFromJob, resetForm],
  )

  return (
    <GenerateFormContext.Provider value={value}>
      {children}
    </GenerateFormContext.Provider>
  )
}

export function useGenerateForm() {
  const ctx = useContext(GenerateFormContext)
  if (!ctx) {
    throw new Error('useGenerateForm must be used within GenerateFormProvider')
  }
  return ctx
}
