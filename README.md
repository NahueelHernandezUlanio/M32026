# Stock y Mantenimiento de Planta

Grupo 3 — Desarrollo de Software — S32 — UTN. Hernandez, Hrynkiewicz, Hurst.

## Estructura

| Carpeta / archivo    | Contenido                                                        | Muestra |
| -------------------- | ---------------------------------------------------------------- | ------- |
| `prototipo/`         | Prototipo estático de las 3 pantallas                            | M2      |
| `openapi.yaml`       | Contrato OpenAPI v0, fuente única de verdad entre front y back   | M2      |
| `api/`               | Backend Node + Express + TS. Por ahora solo `GET /health` real   | M3      |
| `web/`               | SPA React + TS que consume el mock generado del contrato         | M3      |
| `docker-compose.yml` | Levanta `mock` (Prism), `api` y `web`                            | M2/M3   |

## Cómo se conectan

```
navegador ──► web (SPA)
               ├── /api/*   ──► mock Prism generado desde openapi.yaml  (:4010)
               └── /health  ──► api Express real                         (:3000)
```

Los tipos del cliente (`web/src/api/schema.d.ts`) se generan desde `openapi.yaml`, así que si el contrato cambia y el frontend no, el build falla.

## Levantar con Docker

Requiere Docker Desktop.

```
docker compose up --build
```

- SPA: http://localhost:8080
- Mock: http://localhost:4010
- API: http://localhost:3000/health

## Levantar sin Docker

Requiere Node 22+.

```
npm run install:all
npm run dev
```

- SPA: http://localhost:5173 (Vite redirige `/api` al mock y `/health` a la API)

## Scripts

| Script                  | Qué hace                                               |
| ----------------------- | ------------------------------------------------------ |
| `npm run lint:contrato` | Valida `openapi.yaml` con Redocly                      |
| `npm run gen:api`       | Regenera los tipos TS del cliente desde el contrato    |
| `npm run dev`           | Mock + API + SPA en paralelo                           |
| `npm run build`         | Compila API y SPA                                      |

## Forzar respuestas de error en el mock

Prism devuelve el ejemplo del código 2xx por defecto. Para ver otro código del contrato se usa el header `Prefer`:

```
curl -X POST http://localhost:4010/repuestos/REP-6204/usos \
  -H "Content-Type: application/json" \
  -H "Prefer: code=409" \
  -d '{"destino_id":"INC-0042","cantidad":99}'
```
