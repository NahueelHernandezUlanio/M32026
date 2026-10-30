# Flujo del proyecto — M3 y M4

Explicación de cada parte del proyecto: qué es, cómo funciona y cuándo se usa. Al final, el estado frente a M3/M4 y la comparación con los repos de otros equipos de la comisión S32.

## Índice

1. [Cómo encaja todo](#1-cómo-encaja-todo)
2. [El contrato: `openapi.yaml`](#2-el-contrato-openapiyaml)
3. [El prototipo: `prototipo/`](#3-el-prototipo-prototipo)
4. [El backend: `api/`](#4-el-backend-api)
5. [El mock: Prism](#5-el-mock-prism)
6. [La SPA: `web/`](#6-la-spa-web)
7. [Archivos de la raíz](#7-archivos-de-la-raíz)
8. [Flujo típico de trabajo](#8-flujo-típico-de-trabajo)
9. [Estado frente a M3 y M4](#9-estado-frente-a-m3-y-m4)
10. [Comparación con otros equipos](#10-comparación-con-otros-equipos)

---

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
     respuestas inventadas            (contrato)   ─── verifica ──►  tests del backend
```

- **M3:** la SPA funciona contra el **mock** generado del contrato. Del backend real solo consume `/health` (walking skeleton).
- **M4:** el backend real implementa **todo el contrato** con reglas de negocio, base de datos, auth por roles y tests. La SPA sigue contra el mock; conectarla al backend real es la integración de **M5**.

---

## 2. El contrato: `openapi.yaml`

**Qué es:** un documento que define cada endpoint de la API: la URL, el método, qué datos recibe, qué devuelve y qué errores puede dar. Es el acuerdo entre frontend y backend.

**Qué tiene (versión 0.2, 14 operaciones):**

| Endpoint | Para qué | Roles |
|---|---|---|
| `GET /health` | ¿Está vivo el servicio? | Público |
| `GET /auth/me` | Quién soy según el token | Todos |
| `POST /incidencias` | Reportar una incidencia, con fotos | Operario, Mantenimiento, Encargado |
| `POST /incidencias/{codigo}/reparacion` | Pasar una incidencia de REPORTADA a EN_REPARACION | Mantenimiento, Encargado |
| `GET /destinos-uso` | Incidencias en reparación (a dónde se puede imputar un repuesto) | Mantenimiento, Encargado |
| `GET /repuestos/{codigo}` | Datos y stock (físico, reservado, disponible) de un repuesto | Todos |
| `POST /repuestos/{codigo}/usos` | Registrar un uso y descontar stock (RN-01, RN-02, RN-05) | Mantenimiento, Encargado |
| `POST /repuestos/{codigo}/recepciones` | Cargar stock recibido con lote, ubicación y remito (RN-08) | Mantenimiento, Encargado |
| `GET /ubicaciones` | Ubicaciones del almacén | Todos |
| `GET /reservas` | Reservas activas | Todos |
| `POST /reservas` | Reservar unidades para un preventivo (RN-05) | Mantenimiento, Encargado |
| `POST /reservas/{codigo}/liberacion` | Liberar una reserva, con aviso inmediato (RN-05) | **Solo Encargado** |
| `POST /reservas/{codigo}/ejecucion` | Ejecutar el preventivo: descuenta stock y libera la reserva (RN-10) | Mantenimiento, Encargado |

Cada respuesta trae **ejemplos** (por ejemplo `REP-6204`, `Rodamiento 6204`, stock 12). El mock devuelve justamente esos ejemplos.

**Errores:** todos tienen la misma forma `{codigo, mensaje}`:

| HTTP | Cuándo | Códigos |
|---|---|---|
| 401 | Falta el token o no es válido | `NO_AUTENTICADO` |
| 403 | El rol no permite la operación | `PERMISO_DENEGADO` |
| 404 | No existe el repuesto, la máquina, la incidencia, la reserva o la ubicación | `NO_ENCONTRADO` |
| 409 | Se viola una regla de negocio | `STOCK_INSUFICIENTE`, `STOCK_RESERVADO`, `DESTINO_INVALIDO`, `RESERVA_NO_ACTIVA`, `TRANSICION_INVALIDA` |
| 422 | El request no cumple el contrato | `DATOS_INVALIDOS` |

**Cuándo se usa:** cada vez que se agrega o cambia algo de la API, se empieza por acá. Después se regeneran los tipos de la SPA y se corren los tests del backend: si el backend no coincide con el contrato, `test_contrato.py` falla.

**`redocly.yaml`:** configuración del validador del contrato (`pnpm run lint:contrato`), con reglas mínimas.

---

## 3. El prototipo: `prototipo/`

Es el HTML y CSS estático de las 3 pantallas. No se conecta a nada: los datos están escritos a mano en el HTML. Queda como entregable de M2, y su CSS se reusó en la SPA.

---

## 4. El backend: `api/`

FastAPI + SQLModel + Alembic, gestionado con **uv**. Es el stack que fija la cátedra.

### 4.1 Arquitectura en capas

```
  routers/        HTTP: recibe el request, valida formato, chequea rol, arma la respuesta
     │
     ▼
  services.py     Reglas de negocio (RN-01, RN-02, RN-05, RN-08, RN-10). No sabe nada de HTTP
     │
     ▼
  repositories.py Acceso a datos: consultas SQL y bloqueos. No sabe nada de reglas
     │
     ▼
  models.py       Tablas (SQLModel)  ──►  PostgreSQL (siempre en Docker)
```

Cada capa solo conoce a la de abajo. Por eso las reglas se pueden testear llamando directo al servicio, sin HTTP, y el día de mañana se puede cambiar la base sin tocar las reglas.

### 4.2 Archivos de `app/`

| Archivo | Qué hace |
|---|---|
| `main.py` | Crea la app FastAPI, registra los routers, `/health`, `/auth/me` y los manejadores que convierten errores en `{codigo, mensaje}` |
| `models.py` | Las 9 tablas: `Maquina`, `Ubicacion`, `Repuesto`, `Incidencia`, `FotoIncidencia`, `LineaUso`, `Reserva`, `Recepcion`, `MovimientoStock`. También los enums (roles, turnos, estados, tipos de movimiento) y las restricciones `CHECK` (stock ≥ 0, cantidad ≥ 1) |
| `repositories.py` | Patrón **Repository**: una clase por agregado con las consultas. `bloquear=True` hace `SELECT … FOR UPDATE` (ver ADR 0001) |
| `services.py` | **Service Layer**: `StockService` (consultar, usar, recibir), `IncidenciaService` (reportar, pasar a reparación, destinos) y `ReservaService` (reservar, liberar, ejecutar). Acá están las reglas de negocio |
| `routers/` | Endpoints HTTP agrupados: `incidencias.py`, `repuestos.py`, `reservas.py` |
| `schemas.py` | Formas de request y response (Pydantic), iguales a las del contrato |
| `auth.py` | **Auth stub**: 4 tokens fijos, uno por rol. `requiere_rol(...)` corta con 403 si el rol no corresponde |
| `notificaciones.py` | **Puerto de notificación** (RN-09) con un adaptador falso que escribe en el log: alertas de umbral y reservas liberadas |
| `errores.py` | Errores de dominio (`NoEncontrado`, `ReglaDeNegocio`, `PermisoDenegado`, `NoAutenticado`) con su código HTTP |
| `dependencias.py` | Arma cada servicio con su sesión de base y su notificador (inyección de dependencias de FastAPI) |
| `almacenamiento.py` | Guarda fotos y remitos en disco (`UPLOAD_DIR`) con nombre único |
| `db.py` / `config.py` | Conexión a la base. La URL sale de `DATABASE_URL`: si no está, apunta al PostgreSQL del compose en `localhost:5432` |
| `seed.py` | Carga datos de ejemplo si la base está vacía: 3 ubicaciones, 3 máquinas, 2 repuestos (`REP-6204` con stock 12 y mínimo 5, `REP-0100`) y 2 incidencias en reparación (`INC-0001`, `INC-0002`) |

### 4.3 Cómo se cumplen las reglas de negocio

| Regla | Dónde | Qué hace |
|---|---|---|
| **RN-01** Descuento por uso | `StockService.registrar_uso` | Descuenta la cantidad del stock físico. Si no alcanza → 409 `STOCK_INSUFICIENTE` y no se registra nada. Además la base tiene `CHECK (stock_fisico >= 0)` |
| **RN-02** Umbral | `StockService._estado_con_alerta` y `ReservaService.reservar` | Si `stock disponible ≤ umbral mínimo`, devuelve `alerta_umbral: true` y notifica |
| **RN-05** Reserva | `StockService.registrar_uso` y `ReservaService.liberar` | Las unidades reservadas no se pueden usar en otra incidencia (409 `STOCK_RESERVADO`). Solo un Encargado puede liberar (403 si no), y se notifica de inmediato |
| **RN-08** Carga de compra | `StockService.registrar_recepcion` | Suma stock físico y actualiza lote y ubicación |
| **RN-10** Consumo de reserva | `ReservaService.ejecutar` | Descuenta stock físico y libera la reserva en **una sola transacción** |
| **Decisión 4** Turno | `turno_de` | Si no viene el turno, se deriva de la hora del reporte en horario de planta (Argentina) |

Cada operación además deja un **movimiento de stock** inmutable (`entrada`, `reserva`, `liberacion`, `consumo`), que es la base de la trazabilidad (RN-06).

### 4.4 Concurrencia (ADR 0001)

Si dos empleados usan la última unidad al mismo tiempo, el servicio bloquea la fila del repuesto (`SELECT … FOR UPDATE`) antes de validar: el segundo espera y lee el stock ya actualizado. La `CHECK` de la base es la última barrera. La justificación completa, con las alternativas comparadas, está en [docs/adr/0001-concurrencia-rn01.md](docs/adr/0001-concurrencia-rn01.md).

### 4.5 Migraciones (Alembic)

- `alembic/versions/` tiene la migración `esquema inicial`, que crea las 9 tablas.
- Al arrancar, el contenedor corre `alembic upgrade head` y después `python -m app.seed`.
- Cuando se cambie un modelo: `uv run alembic revision --autogenerate -m "descripcion"` dentro de `api/`.

### 4.6 Tests (`tests/`)

pytest + TestClient contra la base `planta_test` del mismo PostgreSQL del compose (la URL sale de `TEST_DATABASE_URL`). Antes de cada test se vacían las tablas con los ids reiniciados y se carga el seed. Cada test usa además un notificador falso que registra los avisos.

| Archivo | Qué prueba |
|---|---|
| `test_rn01_descuento_por_uso.py` | Descuento correcto, uso exacto de todo el stock, rechazo si no alcanza (sin efectos), cantidades inválidas, destino que no está en reparación, la `CHECK` de la base |
| `test_rn02_umbral.py` | Sin alerta por encima del mínimo, alerta al igualarlo y por debajo, umbral evaluado sobre el disponible, alerta al reservar, prueba directa del servicio |
| `test_rn05_reservas.py` | Reservar sin tocar el físico, no reservar de más, no usar lo reservado, usar la parte libre, solo Encargado libera (3 roles rechazados), aviso inmediato, no liberar dos veces, RN-10 |
| `test_auth_y_endpoints.py` | 401 sin token, permisos por rol, `/auth/me`, incidencias con fotos, paso a reparación, turno derivado, RN-08 con remito, ubicaciones |
| `test_contrato.py` | El backend implementa exactamente las operaciones de `openapi.yaml`, con los mismos códigos de éxito |

Se corren con `pnpm test` desde la raíz (50 tests).

### 4.7 Docker

- `Dockerfile`: imagen `python:3.13-slim` con uv. Instala dependencias desde `uv.lock`, corre migraciones y seed, y levanta uvicorn en el puerto 8000. Trae un `HEALTHCHECK` sobre `/health`.
- `.dockerignore`: deja afuera `.venv`, tests y uploads.

---

## 5. El mock: Prism

**Qué es:** Prism **lee `openapi.yaml` y levanta un servidor falso** en el puerto 4010, que responde cada endpoint con los ejemplos del contrato. No tiene código propio: si cambiás el contrato, cambia el mock.

**Para qué sirve:** el frontend se desarrolla y se prueba contra respuestas realistas sin depender del backend.

**Además valida:**
- Si la SPA manda algo que no cumple el contrato (por ejemplo, le falta un campo obligatorio), Prism lo rechaza.
- Desde M4 también exige el header `Authorization: Bearer …`, igual que el backend real (sin él devuelve 401).

**Forzar errores:** por defecto devuelve la respuesta exitosa. Para mostrar un error en una demo se manda el header `Prefer: code=…` (el comando está en el README).

---

## 6. La SPA: `web/`

React + TypeScript + Vite, con **pnpm**.

### 6.1 Conexión con el contrato (`src/api/`)

| Archivo | Qué hace |
|---|---|
| `schema.d.ts` | **Generado automáticamente** desde `openapi.yaml` con `pnpm run gen:api`. No se edita a mano. Contiene los tipos TypeScript de todos los endpoints |
| `client.ts` | Crea el cliente HTTP (`openapi-fetch`) usando esos tipos: si escribís mal una URL o un campo, **TypeScript no compila**. Agrega a cada request el token del rol elegido. También tiene `obtenerHealth()` y `mensajeDeError()` |
| `useRepuesto.ts` | Hook que reusan las dos pantallas de stock: busca un repuesto por código |

### 6.2 Pantallas (`src/pages/`)

**`Incidencia.tsx`**
- Formulario de máquina, descripción, fotos y turno (preseleccionado según la hora).
- Envía a `POST /incidencias` y muestra el ID y el estado.

**`RegistrarUso.tsx`**
- Carga el repuesto (con el stock reservado, si hay) y la lista de destinos.
- Registra el uso y muestra el stock resultante, el aviso de umbral (RN-02) o el error (409).

**`CargarStock.tsx`**
- Carga el repuesto y las ubicaciones.
- Envía lote, cantidad, ubicación y remito, y muestra el stock resultante.

### 6.3 Estructura general

**`App.tsx`**
- Header con el selector **"Ingresar como"** (auth stub: Operario, Mantenimiento, Encargado, Gerencia) y las 3 pestañas. La navegación usa el `#` de la URL, igual que el prototipo.
- Al cambiar de rol, la pantalla se recarga con el token nuevo.
- Footer con el indicador **"Servicio: en línea / sin conexión"**, que consulta el `/health` real de FastAPI.

**Otros archivos:** `main.tsx` monta la app; `styles.css` es el CSS del prototipo más el selector de rol y el indicador de servicio.

### 6.4 Cómo llega la SPA al mock y a la API

| Entorno | Archivo | Qué hace |
|---|---|---|
| Desarrollo | `vite.config.ts` | El servidor de Vite (5173) redirige `/api/*` al mock (4010, sacándole el `/api`) y `/health` a FastAPI (8000) |
| Docker | `nginx.conf` + `Dockerfile` | Compila la SPA con pnpm y la sirve con nginx en el 8080, con las mismas redirecciones hacia los contenedores `mock` y `api` |

---

## 7. Archivos de la raíz

### `docker-compose.yml`

Levanta los 4 servicios con `docker compose up --build`. Requiere Docker Desktop instalado.

| Servicio | Qué es | Puerto |
|---|---|---|
| `db` | PostgreSQL 16, con los datos en un volumen. Es la única base del proyecto: también la usan la API local y los tests | 5432 |
| `mock` | Prism 5.14.3 leyendo `openapi.yaml` | 4010 |
| `api` | FastAPI. Espera a que la base esté lista, migra, carga el seed y arranca | 8000 (Swagger en `/docs`) |
| `web` | La SPA servida con nginx | 8080 → http://localhost:8080 |

### `package.json`

Scripts para trabajar en local (con pnpm). La base siempre corre en Docker:

| Comando | Cuándo usarlo |
|---|---|
| `pnpm run install:all` | Una vez, después de clonar: instala todo (JS con pnpm, Python con uv) |
| `pnpm run db` | Levanta solo PostgreSQL en Docker y espera a que esté listo |
| `pnpm run dev` | Para trabajar día a día: `db` + mock + API + SPA (http://localhost:5173) |
| `pnpm test` | Antes de cada PR: levanta `db` y corre los tests del backend |
| `pnpm run lint:contrato` | Después de editar `openapi.yaml` |
| `pnpm run gen:api` | Después de editar `openapi.yaml`, para regenerar los tipos de la SPA |
| `pnpm run build` | Para comprobar que la SPA compila |

### Otros

- `README.md`: instrucciones para levantar el proyecto.
- `docs/adr/`: decisiones de arquitectura.
- `.gitignore`: deja afuera dependencias, compilados, `.venv` y archivos subidos.

---

## 8. Flujo típico de trabajo

1. Hay que agregar algo a la API → editás `openapi.yaml`.
2. `pnpm run lint:contrato`: verificás que el contrato es válido.
3. `pnpm run gen:api`: regenerás los tipos. TypeScript te marca qué ajustar en la SPA.
4. Implementás el endpoint en el backend: modelo → repositorio → servicio → router.
5. Si cambió un modelo, generás la migración con Alembic.
6. Escribís el test de la regla y corrés `pnpm test`. `test_contrato.py` confirma que el backend sigue igual al contrato.
7. `pnpm run dev`: probás la SPA contra el mock y la API en http://localhost:8000/docs.

---

## 9. Estado frente a M3 y M4

### M3 — SPA contra el contrato

| Requisito | Estado |
|---|---|
| SPA React + TS | ✅ |
| Consume el mock generado del contrato | ✅ Prism + tipos generados |
| Walking skeleton: `/health` real | ✅ FastAPI |
| Desplegado con `docker compose up` | ⚠️ El compose está completo, pero no se probó en esta PC (falta Docker Desktop) |

### M4 — Backend + reglas + tests

| Requisito | Estado |
|---|---|
| API FastAPI + SQLModel | ✅ Con Alembic y PostgreSQL en el compose |
| Repository + Service Layer | ✅ `repositories.py` + `services.py` |
| Tests de RN-01, RN-02 y RN-05 | ✅ 50 tests en verde (también RN-08, RN-10, auth y contrato) |
| Auth stub con roles | ✅ 4 roles del dominio |
| ADR de concurrencia de RN-01 | ✅ `docs/adr/0001-concurrencia-rn01.md` |

### Pendiente

- Probar `docker compose up --build` con Docker Desktop.
- Subir el repo a GitHub y trabajar con PRs revisados por otro integrante (Definition of Done de la cátedra).
- Trazabilidad completa pedido → recepción → uso (RN-06): la recepción todavía no se asocia a un pedido de compra.
- Tests de frontend con Vitest (stack de la cátedra), pendientes para M5.

---

## 10. Comparación con otros equipos

Repos revisados (forks del repo de la cátedra, mismo dominio: `docs/dominio/dominio.md` idéntico en los tres):

| Repo | Integrantes |
|---|---|
| [ecaracasdev/TCI_S32_2026](https://github.com/ecaracasdev/TCI_S32_2026) | Elias Caracas, Martin Carrasco, Nicolas Pieroni |
| [lucadiazg/TCI_S32_2026](https://github.com/lucadiazg/TCI_S32_2026) | Luca Diaz Guevara, Maria Constanza Nosetti, Zoe Valentina Puebla |
| [NahuelIroz/TCI_S32_2026](https://github.com/NahuelIroz/TCI_S32_2026) | Nahuel Iroz, Lucas Esteban |

Revisados el 29/10. Ninguno marcó una entrega formal (no hay tag ni release).

### 10.1 Contra lo que pide M3

| | **Nuestro** | **lucadiazg** | **ecaracasdev** | **NahuelIroz** |
|---|---|---|---|---|
| SPA React + TS | ✅ React 18 | ✅ React 19 + Tailwind | ❌ Es **Angular** 21 | ✅ React 19 |
| Consume el mock generado del contrato | ✅ Prism + tipos **generados** del contrato | ✅ Prism, pero con tipos **escritos a mano** | ❌ JSON estáticos en `public/mock` | ❌ Tiene un script de Prism, pero la SPA usa datos fijos de `src/data/*.ts` (no hace ni un `fetch`) |
| `/health` real | ✅ FastAPI | ⚠️ FastAPI `/api/health`, pero sin Dockerfile y fuera del compose | ✅ FastAPI, con Dockerfile y en el compose | ❌ No tiene backend |
| `docker compose` | db + mock + api + web | Solo Prism | backend + frontend, sin mock | No tiene (solo un Dockerfile del front) |
| Las 3 pantallas | ✅ | ✅ | Solo inicio y dashboard | ✅ y más (login, roles, scanner QR) |

**Conclusión:** en cumplimiento estricto de M3, el nuestro es el más completo.
- **lucadiazg** es lo más parecido, aunque su backend no queda levantado por el compose.
- **ecaracasdev** tiene el backend más avanzado de los tres (base de datos, autenticación), pero usó Angular y un mock que no sale del contrato.
- **NahuelIroz** tiene la interfaz más rica, pero sin backend ni conexión al mock.

### 10.2 Lo que hicieron mejor y cómo quedó en el nuestro

| Punto | Quién | Estado en el nuestro |
|---|---|---|
| **Trazabilidad (RN-06):** recepción en `/pedidos/{id}/recepciones` y uso en `/reparaciones/{id}/usos` | lucadiazg | ⏳ Pendiente: la recepción sigue colgada del repuesto, sin pedido de compra |
| **Stock físico vs. disponible** (RN-01 descuenta del físico) | lucadiazg | ✅ Resuelto en M4: el contrato y el backend devuelven `stock_fisico`, `stock_reservado` y `stock_disponible` |
| **Versión de Prism fija** | lucadiazg | ✅ Resuelto en M4: `stoplight/prism:5.14.3` |
| **Versionado de la API** con prefijo `/api/v0` | ecaracasdev | Opcional, no aplicado |
