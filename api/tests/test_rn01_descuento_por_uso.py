"""RN-01: usar un repuesto descuenta del stock físico la cantidad; el resultado nunca es negativo."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models import LineaUso, MovimientoStock, Rol, TipoMovimiento
from tests.conftest import auth, repuesto

MANTENIMIENTO = auth(Rol.MANTENIMIENTO)


def test_descuenta_la_cantidad_usada_del_stock_fisico(client, session):
    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": 3},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["stock_fisico"] == 9
    assert repuesto(session).stock_fisico == 9


def test_registra_la_linea_de_uso_y_el_movimiento_de_consumo(client, session):
    client.post("/repuestos/REP-6204/usos", headers=MANTENIMIENTO, json={"destino_id": "INC-0001", "cantidad": 2})

    linea = session.exec(select(LineaUso)).one()
    movimiento = session.exec(select(MovimientoStock)).one()
    assert (linea.cantidad, linea.incidencia_id) == (2, 1)
    assert (movimiento.tipo, movimiento.cantidad, movimiento.referencia) == (TipoMovimiento.CONSUMO, 2, "INC-0001")


def test_permite_usar_exactamente_todo_el_stock(client, session):
    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": 12},
    )

    assert respuesta.status_code == 201
    assert repuesto(session).stock_fisico == 0


def test_rechaza_el_uso_si_la_cantidad_supera_el_stock(client, session):
    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": 13},
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "STOCK_INSUFICIENTE"
    assert repuesto(session).stock_fisico == 12
    assert session.exec(select(LineaUso)).first() is None


@pytest.mark.parametrize("cantidad", [0, -1])
def test_rechaza_cantidades_menores_a_uno(client, session, cantidad):
    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": cantidad},
    )

    assert respuesta.status_code == 422
    assert repuesto(session).stock_fisico == 12


def test_rechaza_el_uso_en_una_incidencia_que_no_esta_en_reparacion(client, session):
    nueva = client.post(
        "/incidencias",
        headers=auth(Rol.OPERARIO),
        data={"codigo_maquina": "MAQ-0003", "descripcion": "Banda desalineada"},
    ).json()

    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": nueva["id"], "cantidad": 1},
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "DESTINO_INVALIDO"
    assert repuesto(session).stock_fisico == 12


def test_repuesto_inexistente_devuelve_404(client):
    respuesta = client.post(
        "/repuestos/NO-EXISTE/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": 1},
    )

    assert respuesta.status_code == 404


def test_la_base_impide_stock_fisico_negativo(session):
    """Última barrera ante concurrencia (ADR 0001): la CHECK de la tabla rechaza el valor."""
    rodamiento = repuesto(session)
    rodamiento.stock_fisico = -1
    session.add(rodamiento)

    with pytest.raises(IntegrityError):
        session.commit()
