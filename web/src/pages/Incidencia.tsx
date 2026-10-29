import { useState, type FormEvent } from 'react'
import { api, mensajeDeError } from '../api/client'

type Turno = 'manana' | 'tarde' | 'noche'

function turnoActual(): Turno {
  const hora = new Date().getHours()
  if (hora >= 6 && hora < 14) return 'manana'
  if (hora >= 14 && hora < 22) return 'tarde'
  return 'noche'
}

export default function Incidencia() {
  const [creada, setCreada] = useState<{ id?: string; estado?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const formulario = evento.currentTarget
    const datos = new FormData(formulario)

    setEnviando(true)
    setError(null)
    setCreada(null)

    const { data, error } = await api.POST('/incidencias', {
      body: {
        codigo_maquina: String(datos.get('codigo_maquina')),
        descripcion: String(datos.get('descripcion')),
        turno: datos.get('turno') as Turno,
      },
      bodySerializer: () => datos,
    })

    setEnviando(false)
    if (data) {
      setCreada(data)
      formulario.reset()
    } else {
      setError(mensajeDeError(error, 'No se pudo registrar la incidencia.'))
    }
  }

  return (
    <section className="vista">
      <form onSubmit={enviar}>
        <div className="campo">
          <label htmlFor="codigo-maquina">Máquina</label>
          <input type="text" id="codigo-maquina" name="codigo_maquina" placeholder="Código QR de la máquina" required />
        </div>

        <div className="campo">
          <label htmlFor="descripcion">Descripción del problema</label>
          <textarea id="descripcion" name="descripcion" placeholder="Describí el problema que observaste…" rows={4} required />
        </div>

        <div className="campo">
          <label htmlFor="foto">Fotos</label>
          <input type="file" id="foto" name="fotos" accept="image/*" multiple />
        </div>

        <div className="campo">
          <label htmlFor="turno">Turno</label>
          <select id="turno" name="turno" defaultValue={turnoActual()} required>
            <option value="manana">Mañana</option>
            <option value="tarde">Tarde</option>
            <option value="noche">Noche</option>
          </select>
        </div>

        <button type="submit" className="btn-principal" disabled={enviando}>
          {enviando ? 'Enviando…' : 'Enviar'}
        </button>
      </form>

      {creada && (
        <div className="mensaje-alerta" role="status">
          <p>
            Incidencia {creada.id} registrada. Estado: {creada.estado}
          </p>
        </div>
      )}
      {error && (
        <div className="mensaje-error" role="alert">
          <p>{error}</p>
        </div>
      )}
    </section>
  )
}
