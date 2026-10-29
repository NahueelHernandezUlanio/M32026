import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, type Repuesto } from './client'

export function useRepuesto(codigoInicial: string) {
  const [repuesto, setRepuesto] = useState<Repuesto | null>(null)
  const [error, setError] = useState<string | null>(null)

  const buscar = useCallback(async (codigo: string) => {
    setError(null)
    const { data, error } = await api.GET('/repuestos/{codigo}', {
      params: { path: { codigo } },
    })
    if (data) {
      setRepuesto(data)
    } else {
      setRepuesto(null)
      setError(mensajeDeError(error, 'No se pudo obtener el repuesto.'))
    }
  }, [])

  useEffect(() => {
    buscar(codigoInicial)
  }, [buscar, codigoInicial])

  return { repuesto, setRepuesto, error, buscar }
}
