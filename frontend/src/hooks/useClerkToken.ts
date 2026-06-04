import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { setAuthTokenGetter } from '@/lib/api'

/**
 * Registra el getter del token de Clerk en el cliente axios.
 * Montar este hook una vez en el App shell (ya está en App.tsx).
 */
export function useClerkToken() {
  const { getToken } = useAuth()

  useEffect(() => {
    setAuthTokenGetter(() => getToken())
  }, [getToken])
}
