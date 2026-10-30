import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Rol = components['schemas']['Rol']
export type Repuesto = components['schemas']['Repuesto']
export type DestinoUso =
  paths['/destinos-uso']['get']['responses'][200]['content']['application/json'][number]
export type ApiError = components['schemas']['Error']

type Health = paths['/health']['get']['responses'][200]['content']['application/json']

export const ROLES: { rol: Rol; etiqueta: string; token: string }[] = [
  { rol: 'OPERARIO', etiqueta: 'Operario', token: 'token-operario' },
  { rol: 'MANTENIMIENTO', etiqueta: 'Mantenimiento', token: 'token-mantenimiento' },
  { rol: 'ENCARGADO', etiqueta: 'Encargado', token: 'token-encargado' },
  { rol: 'CONSULTA', etiqueta: 'Gerencia (consulta)', token: 'token-consulta' },
]

let tokenActual = ROLES[1].token

export function usarRol(rol: Rol) {
  tokenActual = ROLES.find((item) => item.rol === rol)?.token ?? tokenActual
}

export const api = createClient<paths>({ baseUrl: '/api' })

api.use({
  onRequest({ request }) {
    request.headers.set('Authorization', `Bearer ${tokenActual}`)
    return request
  },
})

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
