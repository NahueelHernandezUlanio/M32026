import { useEffect, useState, type FormEvent } from 'react'
import { api, mensajeDeError, type DestinoUso } from '../api/client'
import { useRepuesto } from '../api/useRepuesto'

const CODIGO_INICIAL = 'REP-6204'

export default function RegistrarUso() {
  const [codigo, setCodigo] = useState(CODIGO_INICIAL)
  const { repuesto, setRepuesto, error: errorRepuesto, buscar } = useRepuesto(CODIGO_INICIAL)
  const [destinos, setDestinos] = useState<DestinoUso[]>([])
  const [destinoId, setDestinoId] = useState('')
  const [cantidad, setCantidad] = useState(1)
  const [confirmacion, setConfirmacion] = useState<string | null>(null)
  const [alertaUmbral, setAlertaUmbral] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.GET('/destinos-uso').then(({ data }) => {
      if (!data) return
      setDestinos(data)
      setDestinoId(data[0]?.id ?? '')
    })
  }, [])

  const destino = destinos.find((item) => item.id === destinoId)

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setEnviando(true)
    setConfirmacion(null)
    setAlertaUmbral(false)
    setError(null)

    const { data, error } = await api.POST('/repuestos/{codigo}/usos', {
      params: { path: { codigo } },
      body: { destino_id: destinoId, cantidad },
    })

    setEnviando(false)
    if (data) {
      setConfirmacion(`Uso registrado. Stock resultante: ${data.stock_disponible}`)
      setAlertaUmbral(Boolean(data.alerta_umbral))
      if (repuesto) setRepuesto({ ...repuesto, stock_disponible: data.stock_disponible })
    } else {
      setError(mensajeDeError(error, 'No se pudo registrar el uso.'))
    }
  }

  return (
    <section className="vista">
      <form onSubmit={registrar}>
        <div className="campo">
          <label htmlFor="uso-codigo-repuesto">Código del repuesto</label>
          <div className="input-con-boton">
            <input
              type="text"
              id="uso-codigo-repuesto"
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
              <dt>Lote:</dt><dd>{repuesto.lote}</dd>
              <dt>Stock disponible:</dt><dd>{repuesto.stock_disponible}</dd>
              {repuesto.stock_reservado > 0 && (
                <>
                  <dt>Reservado:</dt><dd>{repuesto.stock_reservado}</dd>
                </>
              )}
              <dt>Ubicación:</dt><dd>{repuesto.ubicacion}</dd>
            </dl>
          ) : (
            <p className="texto-solo-lectura">{errorRepuesto ?? 'Cargando…'}</p>
          )}
        </div>

        <div className="campo">
          <label htmlFor="destino">Destino</label>
          <select id="destino" value={destinoId} onChange={(evento) => setDestinoId(evento.target.value)} required>
            {destinos.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} · {item.maquina}
              </option>
            ))}
          </select>
          {destino && <p className="texto-solo-lectura">Máquina destino: {destino.maquina}</p>}
        </div>

        <div className="campo">
          <label htmlFor="uso-cantidad">Cantidad</label>
          <input
            type="number"
            id="uso-cantidad"
            min={1}
            value={cantidad}
            onChange={(evento) => setCantidad(Number(evento.target.value))}
            required
          />
        </div>

        <button type="submit" className="btn-principal" disabled={enviando || !repuesto}>
          {enviando ? 'Registrando…' : 'Registrar uso'}
        </button>
      </form>

      {confirmacion && <div className="mensaje-confirmacion" role="status">{confirmacion}</div>}
      {error && (
        <div className="mensaje-error" role="alert">
          <p>{error}</p>
        </div>
      )}
      {alertaUmbral && (
        <div className="mensaje-aviso" role="status">El stock llegó al mínimo. El repuesto pasa a la lista de compras.</div>
      )}
    </section>
  )
}
