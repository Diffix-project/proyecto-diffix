/// <reference types="vite/client" />
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider } from '@clerk/clerk-react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minuto
      retry: 1,
    },
  },
})

const rootEl = document.getElementById('root')!

// Si falta la clave de Clerk en dev, mostrar un mensaje claro en lugar de crashear.
if (!CLERK_KEY) {
  createRoot(rootEl).render(
    <div className="flex min-h-screen items-center justify-center p-8 text-center">
      <div>
        <h1 className="text-xl font-semibold mb-2">Configuración pendiente</h1>
        <p className="text-muted-foreground">
          Falta la variable de entorno{' '}
          <code className="font-mono bg-muted px-1 rounded">VITE_CLERK_PUBLISHABLE_KEY</code>.
          <br />
          Copiá <code className="font-mono bg-muted px-1 rounded">.env.example</code> a{' '}
          <code className="font-mono bg-muted px-1 rounded">.env</code> y agregá tu clave de Clerk.
        </p>
      </div>
    </div>,
  )
} else {
  createRoot(rootEl).render(
    <StrictMode>
      <ClerkProvider publishableKey={CLERK_KEY}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </ClerkProvider>
    </StrictMode>,
  )
}
