import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export const api = createClient<paths>({ baseUrl: '/api' })

export type Repuesto =
  paths['/repuestos/{codigo}']['get']['responses'][200]['content']['application/json']
export type DestinoUso =
  paths['/destinos-uso']['get']['responses'][200]['content']['application/json'][number]
export type ApiError = components['schemas']['Error']

type Health = paths['/health']['get']['responses'][200]['content']['application/json']

export async function obtenerHealth(): Promise<Health> {
  const respuesta = await fetch('/health')
  if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`)
  return respuesta.json()
}

export function mensajeDeError(error: unknown, porDefecto: string): string {
  if (error && typeof error === 'object' && 'mensaje' in error && typeof error.mensaje === 'string') {
    return error.mensaje
  }
  return porDefecto
}
