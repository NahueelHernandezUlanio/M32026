import { useEffect, useState } from 'react'
import { obtenerHealth, ROLES, usarRol, type Rol } from './api/client'
import Incidencia from './pages/Incidencia'
import RegistrarUso from './pages/RegistrarUso'
import CargarStock from './pages/CargarStock'

const VISTAS = [
  { id: 'incidencia', etiqueta: 'Incidencia', titulo: 'Registro de Incidencia', Componente: Incidencia },
  { id: 'uso-repuesto', etiqueta: 'Registrar uso', titulo: 'Registrar uso de repuesto', Componente: RegistrarUso },
  { id: 'carga-stock', etiqueta: 'Cargar stock', titulo: 'Cargar stock', Componente: CargarStock },
] as const

type EstadoServicio = 'verificando' | 'ok' | 'caido'

function vistaDesdeHash() {
  const nombre = location.hash.slice(1)
  return VISTAS.find((vista) => vista.id === nombre) ?? VISTAS[0]
}

export default function App() {
  const [vista, setVista] = useState(vistaDesdeHash)
  const [servicio, setServicio] = useState<EstadoServicio>('verificando')
  const [rol, setRol] = useState<Rol>('MANTENIMIENTO')

  function cambiarRol(nuevo: Rol) {
    usarRol(nuevo)
    setRol(nuevo)
  }

  useEffect(() => {
    const alCambiarHash = () => setVista(vistaDesdeHash())
    window.addEventListener('hashchange', alCambiarHash)
    return () => window.removeEventListener('hashchange', alCambiarHash)
  }, [])

  useEffect(() => {
    document.title = vista.titulo
  }, [vista])

  useEffect(() => {
    obtenerHealth()
      .then((health) => setServicio(health.status === 'ok' ? 'ok' : 'caido'))
      .catch(() => setServicio('caido'))
  }, [])

  const { Componente } = vista

  return (
    <div className="app-container">
      <header>
        <h1>{vista.titulo}</h1>
        <div className="selector-rol">
          <label htmlFor="rol">Ingresar como</label>
          <select id="rol" value={rol} onChange={(evento) => cambiarRol(evento.target.value as Rol)}>
            {ROLES.map((item) => (
              <option key={item.rol} value={item.rol}>
                {item.etiqueta}
              </option>
            ))}
          </select>
        </div>
        <nav aria-label="Navegación principal">
          <ul>
            {VISTAS.map((item) => (
              <li key={item.id}>
                <a href={`#${item.id}`} aria-current={item.id === vista.id ? 'page' : undefined}>
                  {item.etiqueta}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main>
        <Componente key={`${vista.id}-${rol}`} />
      </main>

      <footer>
        <p className={`estado-servicio estado-${servicio}`} role="status">
          Servicio: {servicio === 'verificando' ? 'verificando…' : servicio === 'ok' ? 'en línea' : 'sin conexión'}
        </p>
        <p>Turno tarde</p>
        <p>- GRUPO 3 - Desarrollo de Software - S32 - UTN -</p>
        <p>- HERNANDEZ - HRYNKIEWICZ - HURST -</p>
      </footer>
    </div>
  )
}
