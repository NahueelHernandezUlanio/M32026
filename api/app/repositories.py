from collections.abc import Sequence

from sqlalchemy import func
from sqlmodel import Session, SQLModel, select

from app.models import (
    EstadoIncidencia,
    EstadoReserva,
    Incidencia,
    Maquina,
    Repuesto,
    Reserva,
    Ubicacion,
)


class Repositorio:
    def __init__(self, session: Session) -> None:
        self.session = session

    def agregar(self, *entidades: SQLModel) -> None:
        self.session.add_all(entidades)
        self.session.flush()


class RepuestoRepository(Repositorio):
    def obtener_por_codigo(self, codigo: str, *, bloquear: bool = False) -> Repuesto | None:
        consulta = select(Repuesto).where(Repuesto.codigo == codigo)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.exec(consulta).first()

    def obtener(self, repuesto_id: int, *, bloquear: bool = False) -> Repuesto | None:
        consulta = select(Repuesto).where(Repuesto.id == repuesto_id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.exec(consulta).first()

    def stock_reservado(self, repuesto_id: int) -> int:
        total = self.session.exec(
            select(func.coalesce(func.sum(Reserva.cantidad), 0)).where(
                Reserva.repuesto_id == repuesto_id,
                Reserva.estado == EstadoReserva.ACTIVA,
            )
        ).one()
        return int(total)


class MaquinaRepository(Repositorio):
    def obtener_por_codigo(self, codigo: str) -> Maquina | None:
        return self.session.exec(select(Maquina).where(Maquina.codigo == codigo)).first()


class UbicacionRepository(Repositorio):
    def obtener(self, codigo: str) -> Ubicacion | None:
        return self.session.get(Ubicacion, codigo)

    def listar(self) -> Sequence[Ubicacion]:
        return self.session.exec(select(Ubicacion).order_by(Ubicacion.codigo)).all()


class IncidenciaRepository(Repositorio):
    def obtener(self, incidencia_id: int) -> Incidencia | None:
        return self.session.get(Incidencia, incidencia_id)

    def listar_en_reparacion(self) -> Sequence[tuple[Incidencia, Maquina]]:
        return self.session.exec(
            select(Incidencia, Maquina)
            .join(Maquina, Maquina.id == Incidencia.maquina_id)
            .where(Incidencia.estado == EstadoIncidencia.EN_REPARACION)
            .order_by(Incidencia.id)
        ).all()


class ReservaRepository(Repositorio):
    def obtener(self, reserva_id: int, *, bloquear: bool = False) -> Reserva | None:
        consulta = select(Reserva).where(Reserva.id == reserva_id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.exec(consulta).first()

    def listar_activas(self) -> Sequence[tuple[Reserva, Repuesto]]:
        return self.session.exec(
            select(Reserva, Repuesto)
            .join(Repuesto, Repuesto.id == Reserva.repuesto_id)
            .where(Reserva.estado == EstadoReserva.ACTIVA)
            .order_by(Reserva.id)
        ).all()
