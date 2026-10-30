# Stock y Mantenimiento de Planta

Grupo 3 - Desarrollo de Software - S32 - UTN. Hernandez, Hrynkiewicz, Hurst.

Explicación detallada de cada parte en [flujo.md](flujo.md). Decisiones de arquitectura en [docs/adr/](docs/adr/).

## Estructura

| Carpeta / archivo    | Contenido                                                                      | Muestra |
| -------------------- | ------------------------------------------------------------------------------ | ------- |
| `prototipo/`         | Prototipo estático de las 3 pantallas                                          | M2      |
| `openapi.yaml`       | Contrato OpenAPI, fuente única de verdad entre front y back                   | M2 → M4 |
| `web/`               | SPA React + TS + Vite (pnpm) que consume el mock generado del contrato         | M3      |
| `api/`               | Backend FastAPI + SQLModel + Alembic, con Repository + Service Layer y pytest  | M3 → M4 |
| `docs/adr/`          | Decisiones de arquitectura (ADR 0001: concurrencia de RN-01)                   | M4      |
| `docker-compose.yml` | Levanta `db` (PostgreSQL), `mock` (Prism), `api` y `web`                       | M2 → M4 |

## Levantar con Docker

Requiere Docker Desktop.

```
docker compose up --build
```

| Servicio | URL |
| --- | --- |
| SPA | http://localhost:8080 |
| API real (Swagger) | http://localhost:8000/docs |
| Mock | http://localhost:4010 |

## Levantar en modo desarrollo

Requiere Node 22+, pnpm, uv y Docker Desktop. La única base del proyecto es PostgreSQL: aunque la API, el mock y la SPA corran local, la base siempre corre en Docker (servicio `db`, puerto 5432).

```
pnpm run install:all
pnpm run dev
```

`pnpm run dev` primero levanta `db` con `docker compose up -d --wait db` y después arranca mock, API y SPA.

- SPA: http://localhost:5173
- API real: http://localhost:8000/docs

## Tests

```
pnpm test
```

Levanta `db` si no está corriendo y corre la suite de pytest del backend contra la base `planta_test` del mismo PostgreSQL (se crea sola la primera vez): RN-01, RN-02, RN-05/RN-10, RN-08, auth por roles y conformidad con el contrato.

## Auth stub (M4)

Todas las rutas salvo `/health` piden el header `Authorization: Bearer <token>`:

| Token | Rol |
| --- | --- |
| `token-operario` | OPERARIO |
| `token-mantenimiento` | MANTENIMIENTO |
| `token-encargado` | ENCARGADO |
| `token-consulta` | CONSULTA (gerencia, solo lectura) |

En la SPA se elige con el selector "Ingresar como" del header.

## Scripts

| Script                  | Qué hace                                               |
| ----------------------- | ------------------------------------------------------ |
| `pnpm run lint:contrato`| Valida `openapi.yaml` con Redocly                      |
| `pnpm run gen:api`      | Regenera los tipos TS del cliente desde el contrato    |
| `pnpm run db`           | Levanta solo PostgreSQL en Docker                      |
| `pnpm run dev`          | `db` + mock + API + SPA en paralelo                    |
| `pnpm test`             | `db` + tests del backend                               |
| `pnpm run build`        | Compila la SPA                                         |

## Forzar respuestas de error en el mock

Con el header `Prefer`:

```
curl -X POST http://localhost:4010/repuestos/REP-6204/usos \
  -H "Authorization: Bearer token-mantenimiento" \
  -H "Content-Type: application/json" \
  -H "Prefer: code=409" \
  -d '{"destino_id":"INC-0001","cantidad":99}'
```
