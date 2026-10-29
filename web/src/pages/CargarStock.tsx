import { useEffect, useState, type FormEvent } from 'react'
import { api, mensajeDeError } from '../api/client'
import { useRepuesto } from '../api/useRepuesto'

const CODIGO_INICIAL = 'REP-6204'

export default function CargarStock() {
  const [codigo, setCodigo] = useState(CODIGO_INICIAL)
  const { repuesto, setRepuesto, error: errorRepuesto, buscar } = useRepuesto(CODIGO_INICIAL)
  const [ubicaciones, setUbicaciones] = useState<string[]>([])
  const [confirmacion, setConfirmacion] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.GET('/ubicaciones').then(({ data }) => {
      if (data) setUbicaciones(data)
    })
  }, [])

  async function cargar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const formulario = evento.currentTarget
    const datos = new FormData(formulario)

    setEnviando(true)
    setConfirmacion(null)
    setError(null)

    const { data, error } = await api.POST('/repuestos/{codigo}/recepciones', {
      params: { path: { codigo } },
      body: {
        lote: String(datos.get('lote')),
        cantidad: Number(datos.get('cantidad')),
        ubicacion: String(datos.get('ubicacion')),
      },
      bodySerializer: () => datos,
    })

    setEnviando(false)
    if (data) {
      setConfirmacion(`Stock cargado. Stock resultante: ${data.stock_disponible}`)
      if (repuesto) setRepuesto({ ...repuesto, stock_disponible: data.stock_disponible })
      formulario.reset()
    } else {
      setError(mensajeDeError(error, 'No se pudo cargar el stock.'))
    }
  }

  return (
    <section className="vista">
      <form onSubmit={cargar}>
        <div className="campo">
          <label htmlFor="stock-codigo-repuesto">Código del repuesto</label>
          <div className="input-con-boton">
            <input
              type="text"
              id="stock-codigo-repuesto"
              placeholder="Código QR o de barras"
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value)}
              required
            />
            <button type="button" className="btn-secundario" onClick={() => buscar(codigo)}>
              Buscar
            </button>
          </div>
        </div>

        <div className="campo">
          <span className="etiqueta">Datos del repuesto</span>
          {repuesto ? (
            <dl className="datos-solo-lectura">
              <dt>Nombre:</dt><dd>{repuesto.nombre}</dd>
              <dt>Stock actual:</dt><dd>{repuesto.stock_disponible}</dd>
              <dt>Stock mínimo:</dt><dd>{repuesto.umbral_minimo}</dd>
            </dl>
          ) : (
            <p className="texto-solo-lectura">{errorRepuesto ?? 'Cargando…'}</p>
          )}
        </div>

        <div className="campo">
          <label htmlFor="lote">Lote</label>
          <input type="text" id="lote" name="lote" placeholder="Ej: L-2026-045" required />
        </div>

        <div className="campo">
          <label htmlFor="stock-cantidad">Cantidad recibida</label>
          <input type="number" id="stock-cantidad" name="cantidad" min={1} defaultValue={1} required />
        </div>

        <div className="campo">
          <label htmlFor="ubicacion">Ubicación en depósito</label>
          <select id="ubicacion" name="ubicacion" required>
            {ubicaciones.map((ubicacion) => (
              <option key={ubicacion} value={ubicacion}>
                {ubicacion}
              </option>
            ))}
          </select>
        </div>

        <div className="campo">
          <label htmlFor="remito">Remito</label>
          <input type="file" id="remito" name="remito" accept="image/*,application/pdf" />
        </div>

        <button type="submit" className="btn-principal" disabled={enviando || !repuesto}>
          {enviando ? 'Cargando…' : 'Cargar stock'}
        </button>
      </form>

      {confirmacion && <div className="mensaje-confirmacion" role="status">{confirmacion}</div>}
      {error && (
        <div className="mensaje-error" role="alert">
          <p>{error}</p>
        </div>
      )}
    </section>
  )
}
