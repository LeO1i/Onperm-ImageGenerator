import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { GenerateFormProvider } from './context/GenerateFormContext'
import { Spinner } from './components/Spinner'
import { GeneratePage } from './features/generate/GeneratePage'

const HistoryPage = lazy(() =>
  import('./features/history/HistoryPage').then((m) => ({
    default: m.HistoryPage,
  })),
)
const PromptsPage = lazy(() =>
  import('./features/prompts/PromptsPage').then((m) => ({
    default: m.PromptsPage,
  })),
)
const SettingsPage = lazy(() =>
  import('./features/settings/SettingsPage').then((m) => ({
    default: m.SettingsPage,
  })),
)

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Spinner label="Loading page…" />}>{children}</Suspense>
}

export default function App() {
  return (
    <BrowserRouter>
      <GenerateFormProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<GeneratePage />} />
            <Route
              path="prompts"
              element={
                <LazyPage>
                  <PromptsPage />
                </LazyPage>
              }
            />
            <Route
              path="history"
              element={
                <LazyPage>
                  <HistoryPage />
                </LazyPage>
              }
            />
            <Route
              path="settings"
              element={
                <LazyPage>
                  <SettingsPage />
                </LazyPage>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </GenerateFormProvider>
    </BrowserRouter>
  )
}
