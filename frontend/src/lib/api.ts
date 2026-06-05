/// <reference types="vite/client" />
import axios from 'axios'

// Cliente axios apuntando a la API del backend.
// La baseURL se lee de la variable de entorno; si no está, usa el default de desarrollo.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Patrón para el token de Clerk ---
//
// Clerk no expone el token de forma síncrona fuera de un componente React.
// La solución sin librería extra: el hook useClerkToken (ver hooks/useClerkToken.ts)
// llama a getToken() de Clerk y registra el getter aquí vía setAuthTokenGetter.
// El interceptor llama al getter antes de cada request.
//
// Así el cliente axios queda desacoplado de React y el token siempre está fresco.

type TokenGetter = () => Promise<string | null>

let _getToken: TokenGetter | null = null

/** Llamar desde el hook useClerkToken para registrar el getter del token. */
export function setAuthTokenGetter(getter: TokenGetter) {
  _getToken = getter
}

api.interceptors.request.use(async (config) => {
  if (_getToken) {
    const token = await _getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

export default api
