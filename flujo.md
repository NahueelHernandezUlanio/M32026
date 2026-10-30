# Flujo del proyecto: M3 y M4

Qué es cada parte del proyecto y cómo se conecta con las demás.

## 1. Cómo encaja todo

```
            navegador
                │
                ▼
        web (SPA React)  ─────────────►  /health  ─────►  api (FastAPI)  ──►  db (PostgreSQL)
                │                                         reglas de negocio
                ▼
             /api/*
                │
                ▼
        mock (Prism)  ◄─── lee ───  openapi.yaml  ─── genera ───►  tipos TS de la SPA
     respuestas de ejemplo           (contrato)   ─── verifica ──►  tests del backend
```

- **M3:** la SPA funciona contra el mock generado del contrato. Del backend real solo usa `/health` (walking skeleton).
- **M4:** el backend implementa todo el contrato con reglas de negocio, base de datos, auth por roles y tests. Conectar la SPA al backend real queda para M5.

## 2. El contrato: `openapi.yaml`

Define cada endpoint: URL, método, qué recibe, qué devuelve y qué errores puede dar. Es el acuerdo entre frontend y backend; cualquier cambio en la API empieza por acá.

| Endpoint | Para qué | Roles |
|---|---|---|
| `GET /health` | Estado del servicio | Público |
| `GET /auth/me` | Usuario y rol del token | Todos |
| `POST /incidencias` | Reportar una incidencia con fotos | Operario, Mantenimiento, Encargado |
| `POST /incidencias/{codigo}/reparacion` | Pasar a EN_REPARACION | Mantenimiento, Encargado |
| `GET /destinos-uso` | Incidencias en reparación | Mantenimiento, Encargado |
| `GET /repuestos/{codigo}` | Datos y stock de un repuesto | Todos |
| `POST /repuestos/{codigo}/usos` | Registrar uso (RN-01, RN-02, RN-05) | Mantenimiento, Encargado |
| `POST /repuestos/{codigo}/recepciones` | Cargar stock recibido (RN-08) | Mantenimiento, Encargado |
| `GET /ubicaciones` | Ubicaciones del almacén | Todos |
| `GET /reservas`, `POST /reservas` | Ver y crear reservas (RN-05) | Ver: todos. Crear: Mantenimiento, Encargado |
| `POST /reservas/{codigo}/liberacion` | Liberar una reserva (RN-05) | Solo Encargado |
| `POST /reservas/{codigo}/ejecucion` | Ejecutar el preventivo (RN-10) | Mantenimiento, Encargado |

Todos los errores tienen la forma `{codigo, mensaje}`:

| HTTP | Cuándo | Códigos |
|---|---|---|
| 401 | Falta el token o no es válido | `NO_AUTENTICADO` |
| 403 | El rol no permite la operación | `PERMISO_DENEGADO` |
| 404 | No existe el recurso | `NO_ENCONTRADO` |
| 409 | Se viola una regla de negocio | `STOCK_INSUFICIENTE`, `STOCK_RESERVADO`, `DESTINO_INVALIDO`, `RESERVA_NO_ACTIVA`, `TRANSICION_INVALIDA` |
| 422 | El request no cumple el contrato | `DATOS_INVALIDOS` |

El contrato se valida con Redocly (`pnpm run lint:contrato`).

## 3. El prototipo: `prototipo/`

HTML y CSS estático de las 3 pantallas, entregado en M2. Su CSS se reusó en la SPA.

## 4. El backend: `api/`

FastAPI + SQLModel + Alembic, con uv.

### 4.1 Capas

```
  routers/         HTTP: valida el request, chequea el rol, arma la respuesta
     │
     ▼
  services.py      Reglas de negocio. No sabe nada de HTTP
     │
     ▼
  repositories.py  Consultas a la base y bloqueos. No sabe nada de reglas
     │
     ▼
  models.py        Tablas (SQLModel) ──► PostgreSQL
```

Cada capa solo conoce a la de abajo, así las reglas se pueden testear sin HTTP.

### 4.2 Archivos de `app/`

- `main.py`: crea la app, registra los routers y convierte los errores en `{codigo, mensaje}`.
- `models.py`: las 9 tablas, los enums y las `CHECK` (stock ≥ 0, cantidad ≥ 1).
- `repositories.py` y `services.py`: acceso a datos y reglas de negocio.
- `routers/`: endpoints de incidencias, repuestos y reservas.
- `schemas.py`: formas de request y response, iguales a las del contrato.
- `auth.py`: auth stub con 4 tokens fijos. `requiere_rol(...)` devuelve 403 si el rol no corresponde.
- `notificaciones.py`: puerto de notificación (RN-09) con un adaptador que escribe en el log.
- `seed.py`: datos de ejemplo (`REP-6204` con stock 12 y mínimo 5, incidencias `INC-0001` e `INC-0002`).

### 4.3 Reglas de negocio

| Regla | Dónde | Qué hace |
|---|---|---|
| RN-01 Descuento por uso | `StockService.registrar_uso` | Descuenta del stock físico. Si no alcanza, 409 `STOCK_INSUFICIENTE` |
| RN-02 Umbral | `StockService._estado_con_alerta` | Si disponible ≤ mínimo, devuelve `alerta_umbral: true` y notifica |
| RN-05 Reserva | `registrar_uso` y `ReservaService.liberar` | Lo reservado no se usa (409 `STOCK_RESERVADO`). Solo un Encargado libera, con aviso |
| RN-08 Carga de compra | `StockService.registrar_recepcion` | Suma stock y actualiza lote y ubicación |
| RN-10 Consumo de reserva | `ReservaService.ejecutar` | Descuenta stock y libera la reserva en una sola transacción |

Cada operación deja un movimiento de stock (`entrada`, `reserva`, `liberacion`, `consumo`) para la trazabilidad (RN-06).

### 4.4 Concurrencia

Si dos empleados usan la última unidad a la vez, el servicio bloquea la fila con `SELECT … FOR UPDATE` y la `CHECK` de la base queda como última barrera. Ver [docs/adr/0001-concurrencia-rn01.md](docs/adr/0001-concurrencia-rn01.md).

### 4.5 Migraciones

Al arrancar se corre `alembic upgrade head` y después el seed. Si cambia un modelo: `uv run alembic revision --autogenerate -m "descripcion"` dentro de `api/`.

### 4.6 Tests

pytest + TestClient contra la base `planta_test`. Cada test arranca con las tablas vacías y el seed cargado. Se corren con `pnpm test` (50 tests).

- `test_rn01_descuento_por_uso.py`
- `test_rn02_umbral.py`
- `test_rn05_reservas.py` (incluye RN-10)
- `test_auth_y_endpoints.py` (roles, incidencias, RN-08)
- `test_contrato.py`: el backend implementa exactamente las operaciones de `openapi.yaml`

## 5. El mock: Prism

Prism lee `openapi.yaml` y responde cada endpoint con los ejemplos del contrato, en el puerto 4010. No tiene código propio: si cambiás el contrato, cambia el mock. Rechaza los requests que no cumplen el contrato y exige el token, igual que el backend. Para forzar un error se usa el header `Prefer: code=409` (ver README).

## 6. La SPA: `web/`

React + TypeScript + Vite, con pnpm.

- `src/api/schema.d.ts`: tipos generados del contrato con `pnpm run gen:api`. No se edita a mano.
- `src/api/client.ts`: cliente `openapi-fetch` con esos tipos (si una URL o un campo está mal, no compila). Agrega el token del rol elegido.
- `src/api/useRepuesto.ts`: hook para buscar un repuesto, lo usan dos pantallas.
- `src/pages/`: `Incidencia`, `RegistrarUso` y `CargarStock`.
- `App.tsx`: selector de rol, pestañas (con `#` en la URL) e indicador de `/health` en el footer.

En desarrollo, `vite.config.ts` manda `/api/*` al mock y `/health` a FastAPI. En Docker hace lo mismo `nginx.conf`.

## 7. docker-compose

`docker compose up --build` levanta:

| Servicio | Qué es | Puerto |
|---|---|---|
| `db` | PostgreSQL 16, con volumen | 5432 |
| `mock` | Prism leyendo `openapi.yaml` | 4010 |
| `api` | FastAPI: espera a la base, migra, carga el seed y arranca | 8000 (Swagger en `/docs`) |
| `web` | La SPA servida con nginx | 8080 |

Los scripts para desarrollo local están en el README.

## 8. Flujo de trabajo

1. Editar `openapi.yaml`.
2. `pnpm run lint:contrato` para validarlo.
3. `pnpm run gen:api` para regenerar los tipos; TypeScript marca qué ajustar en la SPA.
4. Implementar en el backend: modelo → repositorio → servicio → router.
5. Si cambió un modelo, generar la migración.
6. Escribir el test de la regla y correr `pnpm test`.
7. Probar con `pnpm run dev`.

## 9. Pendiente

- Trazabilidad completa pedido → recepción → uso (RN-06): la recepción todavía no se asocia a un pedido de compra.
- Tests de frontend con Vitest.
- Test con dos transacciones concurrentes sobre el mismo repuesto.
