"""Puerto de notificación (RN-09) con un adaptador falso que escribe en el log."""

import logging
from typing import Protocol

from app.models import Repuesto, Reserva

logger = logging.getLogger("planta.notificaciones")


class Notificador(Protocol):
    def alerta_umbral(self, repuesto: Repuesto, stock_disponible: int) -> None: ...

    def reserva_liberada(self, reserva: Reserva, repuesto: Repuesto, autorizada_por: str) -> None: ...


class NotificadorLog:
    def alerta_umbral(self, repuesto: Repuesto, stock_disponible: int) -> None:
        logger.warning(
            "Alerta de umbral: %s quedó con %s disponibles (mínimo %s)",
            repuesto.codigo,
            stock_disponible,
            repuesto.umbral_minimo,
        )

    def reserva_liberada(self, reserva: Reserva, repuesto: Repuesto, autorizada_por: str) -> None:
        logger.warning(
            "Reserva %s liberada por %s: %s unidades de %s vuelven a estar disponibles",
            reserva.codigo,
            autorizada_por,
            reserva.cantidad,
            repuesto.codigo,
        )


def get_notificador() -> Notificador:
    return NotificadorLog()
