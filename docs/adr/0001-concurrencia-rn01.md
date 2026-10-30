# ADR 0001: Concurrencia en el descuento de stock (RN-01)

- **Estado:** Aceptada
- **Fecha:** 2026-10-29
- **Muestra:** M4

## Contexto

RN-01 dice que usar un repuesto descuenta del stock físico la cantidad usada y que el stock resultante debe ser ≥ 0. El dominio deja abierto a propósito qué pasa si **dos empleados descuentan la última unidad al mismo tiempo** (hueco deliberado 2, sección 7) y pide resolverlo en M4.

El problema es la secuencia *leer → validar → escribir*:

```
Empleado A: lee stock = 1   ─┐
Empleado B: lee stock = 1    │  los dos validan "1 ≥ 1" ✔
Empleado A: escribe stock = 0│
Empleado B: escribe stock = 0┘  → se usaron 2 unidades y el sistema registra 1 (o -1 con UPDATE relativo)
```

Lo mismo pasa con las reservas (RN-05): una reserva y un uso simultáneos pueden comprometer más unidades que las disponibles, porque `stock disponible = stock físico − stock reservado` se calcula a partir de dos tablas.

## Alternativas

| Alternativa | Cómo funciona | A favor | En contra |
|---|---|---|---|
| **A. Solo `CHECK (stock_fisico >= 0)`** | La base rechaza cualquier escritura que deje stock negativo. | Simple, imposible de saltear desde el código. | No cubre RN-05: el disponible depende de las reservas (otra tabla) y un `CHECK` no puede mirarlas. Con `UPDATE` absoluto (`stock = 0`) tampoco detecta la carrera. Devuelve un error técnico (`IntegrityError`) en lugar del error de negocio. |
| **B. Bloqueo pesimista `SELECT … FOR UPDATE`** | Antes de validar se bloquea la fila del repuesto; el segundo empleado espera a que termine la primera transacción y lee el valor ya actualizado. | Serializa justo lo que hay que serializar (un repuesto) y cubre RN-01 y RN-05 juntos. Los errores siguen siendo de negocio (409 `STOCK_INSUFICIENTE` / `STOCK_RESERVADO`). | Las operaciones sobre **el mismo** repuesto esperan en fila. Hay riesgo de deadlock si dos transacciones bloquean filas en distinto orden. |
| **C. Versionado optimista** | Columna `version`; el `UPDATE` incluye `WHERE version = :leida` y, si no afecta filas, se reintenta. | Sin esperas bajo baja contención. | Hay que implementar reintentos en cada operación. Con mucha contención (la última unidad de un repuesto crítico) los reintentos se multiplican. La reserva también tendría que versionarse. |

## Decisión

**B + A: bloqueo pesimista en el servicio y `CHECK` en la base como última barrera.**

1. Toda operación que lee y modifica stock bloquea primero la fila del repuesto con `SELECT … FOR UPDATE`. Están en `app/services.py` y usan `RepuestoRepository.obtener_por_codigo(..., bloquear=True)`:
   - registrar uso (RN-01, RN-05);
   - registrar recepción (RN-08);
   - crear reserva (RN-05);
   - liberar reserva (RN-05);
   - ejecutar reserva (RN-10).
2. Con la fila bloqueada se calcula el disponible (físico − reservas activas), se valida y se escribe en la **misma transacción**.
3. **Orden de bloqueo fijo:** primero el repuesto y después la reserva (`ReservaService._reserva_activa`). Así dos transacciones nunca se esperan mutuamente (sin deadlocks).
4. La tabla `repuesto` tiene `CHECK (stock_fisico >= 0)` y las líneas de uso, reservas y recepciones tienen `CHECK (cantidad >= 1)`. Si un error de programación saltea el servicio, la base rechaza el dato igual.

## Consecuencias

RN-01 y RN-05 se cumplen bajo concurrencia sin reintentos, el usuario recibe un error de negocio claro y la base garantiza que el stock físico nunca quede negativo.

A cambio, dos operaciones sobre el mismo repuesto esperan una a la otra. Son operaciones de milisegundos y es raro que dos empleados usen el mismo repuesto en el mismo instante.

Los tests cubren la `CHECK` (`test_la_base_impide_stock_fisico_negativo`). Falta un test con dos transacciones concurrentes reales, queda para M5.
