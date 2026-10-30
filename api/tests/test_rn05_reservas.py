"""RN-05: lo reservado no se usa en otra incidencia; liberar exige Encargado y aviso inmediato.
RN-10: ejecutar el preventivo descuenta stock físico y libera la reserva en la misma transacción."""

import pytest
from sqlmodel import select

from app.errores import PermisoDenegado
from app.models import EstadoReserva, MovimientoStock, Reserva, Rol, TipoMovimiento
from app.services import ReservaService
from tests.conftest import auth, repuesto, usuario

MANTENIMIENTO = auth(Rol.MANTENIMIENTO)
ENCARGADO = auth(Rol.ENCARGADO)


def reservar(client, cantidad: int = 10) -> str:
    respuesta = client.post(
        "/reservas",
        headers=MANTENIMIENTO,
        json={"repuesto_codigo": "REP-6204", "cantidad": cantidad, "motivo": "Preventivo caldera"},
    )
    assert respuesta.status_code == 201
    return respuesta.json()["reserva"]["id"]


def usar(client, cantidad: int):
    return client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": cantidad},
    )


def test_reservar_aparta_unidades_sin_tocar_el_stock_fisico(client, session):
    reservar(client, 10)

    detalle = client.get("/repuestos/REP-6204", headers=MANTENIMIENTO).json()
    assert (detalle["stock_fisico"], detalle["stock_reservado"], detalle["stock_disponible"]) == (12, 10, 2)


def test_no_se_puede_reservar_mas_que_lo_disponible(client):
    reservar(client, 10)

    respuesta = client.post(
        "/reservas",
        headers=MANTENIMIENTO,
        json={"repuesto_codigo": "REP-6204", "cantidad": 3, "motivo": "Otro preventivo"},
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "STOCK_INSUFICIENTE"


def test_las_unidades_reservadas_no_se_usan_en_otra_incidencia(client, session):
    reservar(client, 10)

    respuesta = usar(client, 3)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "STOCK_RESERVADO"
    assert repuesto(session).stock_fisico == 12


def test_se_puede_usar_la_parte_no_reservada(client, session):
    reservar(client, 10)

    respuesta = usar(client, 2)

    assert respuesta.status_code == 201
    assert repuesto(session).stock_fisico == 10


@pytest.mark.parametrize("rol", [Rol.MANTENIMIENTO, Rol.OPERARIO, Rol.CONSULTA])
def test_solo_un_encargado_puede_liberar_una_reserva(client, session, notificador, rol):
    codigo = reservar(client)

    respuesta = client.post(f"/reservas/{codigo}/liberacion", headers=auth(rol))

    assert respuesta.status_code == 403
    assert session.exec(select(Reserva)).one().estado == EstadoReserva.ACTIVA
    assert notificador.liberaciones == []


def test_el_encargado_libera_y_se_avisa_de_inmediato(client, notificador):
    codigo = reservar(client)

    respuesta = client.post(f"/reservas/{codigo}/liberacion", headers=ENCARGADO)

    assert respuesta.status_code == 200
    assert respuesta.json()["reserva"]["estado"] == "LIBERADA"
    assert respuesta.json()["stock"]["stock_disponible"] == 12
    assert notificador.liberaciones == [(codigo, "Encargado Demo")]


def test_despues_de_liberar_las_unidades_se_pueden_usar(client):
    codigo = reservar(client, 10)
    client.post(f"/reservas/{codigo}/liberacion", headers=ENCARGADO)

    assert usar(client, 8).status_code == 201


def test_no_se_libera_dos_veces(client):
    codigo = reservar(client)
    client.post(f"/reservas/{codigo}/liberacion", headers=ENCARGADO)

    respuesta = client.post(f"/reservas/{codigo}/liberacion", headers=ENCARGADO)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "RESERVA_NO_ACTIVA"


def test_la_regla_de_liberacion_vive_en_el_servicio(session, notificador):
    servicio = ReservaService(session, notificador)
    reserva, _ = servicio.reservar("REP-6204", 4, "Preventivo", usuario(Rol.MANTENIMIENTO))

    with pytest.raises(PermisoDenegado):
        servicio.liberar(reserva.codigo, usuario(Rol.MANTENIMIENTO))


def test_ejecutar_descuenta_fisico_y_libera_la_reserva_juntos(client, session):
    codigo = reservar(client, 10)

    respuesta = client.post(f"/reservas/{codigo}/ejecucion", headers=MANTENIMIENTO)

    assert respuesta.status_code == 200
    assert respuesta.json()["reserva"]["estado"] == "EJECUTADA"
    assert respuesta.json()["stock"] == {"stock_fisico": 2, "stock_reservado": 0, "stock_disponible": 2}
    tipos = [m.tipo for m in session.exec(select(MovimientoStock).order_by(MovimientoStock.id))]
    assert tipos == [TipoMovimiento.RESERVA, TipoMovimiento.LIBERACION, TipoMovimiento.CONSUMO]


def test_una_reserva_ejecutada_no_se_puede_liberar(client):
    codigo = reservar(client)
    client.post(f"/reservas/{codigo}/ejecucion", headers=MANTENIMIENTO)

    respuesta = client.post(f"/reservas/{codigo}/liberacion", headers=ENCARGADO)

    assert respuesta.status_code == 409
