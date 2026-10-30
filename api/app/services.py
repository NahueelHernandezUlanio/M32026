from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.auth import Usuario
from app.errores import NoEncontrado, PermisoDenegado, ReglaDeNegocio
from app.models import (
    EstadoIncidencia,
    EstadoReserva,
    FotoIncidencia,
    Incidencia,
    LineaUso,
    MovimientoStock,
    Recepcion,
    Repuesto,
    Reserva,
    Rol,
    TipoMovimiento,
    Turno,
    ahora,
)
from app.notificaciones import Notificador
from app.repositories import (
    IncidenciaRepository,
    MaquinaRepository,
    RepuestoRepository,
    ReservaRepository,
    UbicacionRepository,
)

ZONA_PLANTA = ZoneInfo("America/Argentina/Buenos_Aires")


@dataclass(frozen=True)
class EstadoStock:
    repuesto: Repuesto
    stock_reservado: int

    @property
    def stock_disponible(self) -> int:
        return self.repuesto.stock_fisico - self.stock_reservado

    @property
    def bajo_umbral(self) -> bool:
        return self.stock_disponible <= self.repuesto.umbral_minimo


def parsear_codigo(codigo: str, prefijo: str) -> int | None:
    numero = codigo.removeprefix(f"{prefijo}-")
    if numero == codigo or not numero.isdigit():
        return None
    return int(numero)


def turno_de(momento: datetime) -> Turno:
    """Decisión de cátedra 4: el turno se deriva del timestamp del reporte, en hora de planta."""
    hora = momento.astimezone(ZONA_PLANTA).hour
    if 6 <= hora < 14:
        return Turno.MANANA
    if 14 <= hora < 22:
        return Turno.TARDE
    return Turno.NOCHE


def validar_cantidad(cantidad: int) -> None:
    if cantidad < 1:
        raise ReglaDeNegocio("CANTIDAD_INVALIDA", "La cantidad debe ser un entero mayor o igual a 1.")


class StockService:
    def __init__(self, session: Session, notificador: Notificador) -> None:
        self.session = session
        self.notificador = notificador
        self.repuestos = RepuestoRepository(session)
        self.incidencias = IncidenciaRepository(session)
        self.ubicaciones = UbicacionRepository(session)

    def consultar(self, codigo: str) -> EstadoStock:
        repuesto = self._repuesto(codigo)
        return EstadoStock(repuesto, self.repuestos.stock_reservado(repuesto.id))

    def registrar_uso(self, codigo: str, destino_id: str, cantidad: int, usuario: Usuario) -> EstadoStock:
        validar_cantidad(cantidad)
        repuesto = self._repuesto(codigo, bloquear=True)
        incidencia = self._incidencia_en_reparacion(destino_id)
        reservado = self.repuestos.stock_reservado(repuesto.id)
        disponible = repuesto.stock_fisico - reservado

        # RN-01: el stock físico nunca puede quedar negativo.
        if cantidad > repuesto.stock_fisico:
            raise ReglaDeNegocio(
                "STOCK_INSUFICIENTE",
                f"La cantidad supera el stock disponible ({disponible}).",
            )
        # RN-05: las unidades reservadas no se usan en otra incidencia.
        if cantidad > disponible:
            raise ReglaDeNegocio(
                "STOCK_RESERVADO",
                f"Hay {reservado} unidades reservadas para mantenimiento preventivo; "
                f"solo {disponible} están disponibles.",
            )

        repuesto.stock_fisico -= cantidad
        self.repuestos.agregar(
            repuesto,
            LineaUso(repuesto_id=repuesto.id, incidencia_id=incidencia.id, cantidad=cantidad, usuario=usuario.nombre),
            MovimientoStock(
                repuesto_id=repuesto.id,
                tipo=TipoMovimiento.CONSUMO,
                cantidad=cantidad,
                referencia=incidencia.codigo,
                usuario=usuario.nombre,
            ),
        )
        self.session.commit()
        return self._estado_con_alerta(repuesto, reservado)

    def registrar_recepcion(
        self,
        codigo: str,
        lote: str,
        cantidad: int,
        ubicacion_codigo: str,
        remito_ruta: str | None,
        usuario: Usuario,
    ) -> EstadoStock:
        validar_cantidad(cantidad)
        repuesto = self._repuesto(codigo, bloquear=True)
        if self.ubicaciones.obtener(ubicacion_codigo) is None:
            raise NoEncontrado(f"No existe la ubicación {ubicacion_codigo}.")

        # RN-08: al recibir una compra se carga el stock físico y su ubicación.
        repuesto.stock_fisico += cantidad
        repuesto.lote = lote
        repuesto.ubicacion_codigo = ubicacion_codigo
        recepcion = Recepcion(
            repuesto_id=repuesto.id,
            lote=lote,
            cantidad=cantidad,
            ubicacion_codigo=ubicacion_codigo,
            remito_ruta=remito_ruta,
            usuario=usuario.nombre,
        )
        self.repuestos.agregar(repuesto, recepcion)
        self.repuestos.agregar(
            MovimientoStock(
                repuesto_id=repuesto.id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=cantidad,
                referencia=f"REC-{recepcion.id:04d}",
                usuario=usuario.nombre,
            )
        )
        self.session.commit()
        return EstadoStock(repuesto, self.repuestos.stock_reservado(repuesto.id))

    def _estado_con_alerta(self, repuesto: Repuesto, reservado: int) -> EstadoStock:
        # RN-02: se alerta cuando stock disponible <= umbral mínimo.
        estado = EstadoStock(repuesto, reservado)
        if estado.bajo_umbral:
            self.notificador.alerta_umbral(repuesto, estado.stock_disponible)
        return estado

    def _repuesto(self, codigo: str, *, bloquear: bool = False) -> Repuesto:
        repuesto = self.repuestos.obtener_por_codigo(codigo, bloquear=bloquear)
        if repuesto is None:
            raise NoEncontrado(f"No existe un repuesto con código {codigo}.")
        return repuesto

    def _incidencia_en_reparacion(self, destino_id: str) -> Incidencia:
        incidencia_id = parsear_codigo(destino_id, "INC")
        incidencia = self.incidencias.obtener(incidencia_id) if incidencia_id is not None else None
        if incidencia is None:
            raise NoEncontrado(f"No existe la incidencia {destino_id}.")
        if incidencia.estado != EstadoIncidencia.EN_REPARACION:
            raise ReglaDeNegocio(
                "DESTINO_INVALIDO",
                f"La incidencia {destino_id} no está en reparación (estado {incidencia.estado}).",
            )
        return incidencia


class IncidenciaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.incidencias = IncidenciaRepository(session)
        self.maquinas = MaquinaRepository(session)

    def reportar(
        self,
        codigo_maquina: str,
        descripcion: str,
        turno: Turno | None,
        fotos: list[str],
        usuario: Usuario,
        momento: datetime | None = None,
    ) -> Incidencia:
        maquina = self.maquinas.obtener_por_codigo(codigo_maquina)
        if maquina is None:
            raise NoEncontrado(f"No existe una máquina con código {codigo_maquina}.")

        momento = momento or ahora()
        incidencia = Incidencia(
            maquina_id=maquina.id,
            descripcion=descripcion,
            turno=turno or turno_de(momento),
            reportada_por=usuario.nombre,
            creada_en=momento,
        )
        self.incidencias.agregar(incidencia)
        self.incidencias.agregar(*(FotoIncidencia(incidencia_id=incidencia.id, ruta=ruta) for ruta in fotos))
        self.session.commit()
        return incidencia

    def iniciar_reparacion(self, codigo: str) -> Incidencia:
        incidencia_id = parsear_codigo(codigo, "INC")
        incidencia = self.incidencias.obtener(incidencia_id) if incidencia_id is not None else None
        if incidencia is None:
            raise NoEncontrado(f"No existe la incidencia {codigo}.")
        if incidencia.estado != EstadoIncidencia.REPORTADA:
            raise ReglaDeNegocio(
                "TRANSICION_INVALIDA",
                f"Solo una incidencia REPORTADA pasa a reparación (estado actual {incidencia.estado}).",
            )
        incidencia.estado = EstadoIncidencia.EN_REPARACION
        self.incidencias.agregar(incidencia)
        self.session.commit()
        return incidencia

    def destinos_de_uso(self) -> list[tuple[str, str]]:
        return [(incidencia.codigo, maquina.nombre) for incidencia, maquina in self.incidencias.listar_en_reparacion()]


class ReservaService:
    def __init__(self, session: Session, notificador: Notificador) -> None:
        self.session = session
        self.notificador = notificador
        self.repuestos = RepuestoRepository(session)
        self.reservas = ReservaRepository(session)

    def reservar(self, codigo_repuesto: str, cantidad: int, motivo: str, usuario: Usuario) -> tuple[Reserva, EstadoStock]:
        validar_cantidad(cantidad)
        repuesto = self.repuestos.obtener_por_codigo(codigo_repuesto, bloquear=True)
        if repuesto is None:
            raise NoEncontrado(f"No existe un repuesto con código {codigo_repuesto}.")
        reservado = self.repuestos.stock_reservado(repuesto.id)
        disponible = repuesto.stock_fisico - reservado
        if cantidad > disponible:
            raise ReglaDeNegocio(
                "STOCK_INSUFICIENTE",
                f"No se pueden reservar {cantidad} unidades: hay {disponible} disponibles.",
            )

        reserva = Reserva(repuesto_id=repuesto.id, cantidad=cantidad, motivo=motivo, creada_por=usuario.nombre)
        self.reservas.agregar(reserva)
        self.reservas.agregar(self._movimiento(reserva, TipoMovimiento.RESERVA, usuario))
        self.session.commit()

        estado = EstadoStock(repuesto, reservado + cantidad)
        if estado.bajo_umbral:
            self.notificador.alerta_umbral(repuesto, estado.stock_disponible)
        return reserva, estado

    def liberar(self, codigo_reserva: str, usuario: Usuario) -> tuple[Reserva, EstadoStock]:
        # RN-05: liberar una reserva exige autorización de un Encargado y aviso inmediato.
        if usuario.rol != Rol.ENCARGADO:
            raise PermisoDenegado("Solo un Encargado puede autorizar la liberación de una reserva.")

        reserva, repuesto = self._reserva_activa(codigo_reserva)
        reserva.estado = EstadoReserva.LIBERADA
        reserva.cerrada_por = usuario.nombre
        reserva.cerrada_en = ahora()
        self.reservas.agregar(reserva, self._movimiento(reserva, TipoMovimiento.LIBERACION, usuario))
        self.session.commit()

        self.notificador.reserva_liberada(reserva, repuesto, usuario.nombre)
        return reserva, EstadoStock(repuesto, self.repuestos.stock_reservado(repuesto.id))

    def ejecutar(self, codigo_reserva: str, usuario: Usuario) -> tuple[Reserva, EstadoStock]:
        # RN-10: descontar stock físico y liberar la reserva en la misma transacción.
        reserva, repuesto = self._reserva_activa(codigo_reserva)
        repuesto.stock_fisico -= reserva.cantidad
        reserva.estado = EstadoReserva.EJECUTADA
        reserva.cerrada_por = usuario.nombre
        reserva.cerrada_en = ahora()
        self.reservas.agregar(
            repuesto,
            reserva,
            self._movimiento(reserva, TipoMovimiento.LIBERACION, usuario),
            self._movimiento(reserva, TipoMovimiento.CONSUMO, usuario),
        )
        self.session.commit()
        return reserva, EstadoStock(repuesto, self.repuestos.stock_reservado(repuesto.id))

    def listar_activas(self) -> list[tuple[Reserva, Repuesto]]:
        return list(self.reservas.listar_activas())

    def _reserva_activa(self, codigo: str) -> tuple[Reserva, Repuesto]:
        reserva_id = parsear_codigo(codigo, "RES")
        reserva = self.reservas.obtener(reserva_id) if reserva_id is not None else None
        if reserva is None:
            raise NoEncontrado(f"No existe la reserva {codigo}.")

        # Se bloquea primero el repuesto y después la reserva: mismo orden que en registrar_uso.
        repuesto = self.repuestos.obtener(reserva.repuesto_id, bloquear=True)
        reserva = self.reservas.obtener(reserva.id, bloquear=True)
        if reserva.estado != EstadoReserva.ACTIVA:
            raise ReglaDeNegocio("RESERVA_NO_ACTIVA", f"La reserva {codigo} ya está {reserva.estado}.")
        return reserva, repuesto

    @staticmethod
    def _movimiento(reserva: Reserva, tipo: TipoMovimiento, usuario: Usuario) -> MovimientoStock:
        return MovimientoStock(
            repuesto_id=reserva.repuesto_id,
            tipo=tipo,
            cantidad=reserva.cantidad,
            referencia=reserva.codigo,
            usuario=usuario.nombre,
        )
