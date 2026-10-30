"""RN-02: cuando stock disponible <= umbral mínimo se genera una alerta."""

from app.models import Rol
from app.services import StockService
from tests.conftest import auth, usuario

MANTENIMIENTO = auth(Rol.MANTENIMIENTO)


def usar(client, cantidad: int):
    return client.post(
        "/repuestos/REP-6204/usos",
        headers=MANTENIMIENTO,
        json={"destino_id": "INC-0001", "cantidad": cantidad},
    )


def test_no_alerta_si_el_disponible_queda_por_encima_del_umbral(client, notificador):
    respuesta = usar(client, 6)

    assert respuesta.json()["stock_disponible"] == 6
    assert respuesta.json()["alerta_umbral"] is False
    assert notificador.alertas == []


def test_alerta_cuando_el_disponible_iguala_el_umbral(client, notificador):
    respuesta = usar(client, 7)

    assert respuesta.json()["stock_disponible"] == 5
    assert respuesta.json()["alerta_umbral"] is True
    assert notificador.alertas == [("REP-6204", 5)]


def test_alerta_cuando_el_disponible_queda_debajo_del_umbral(client, notificador):
    respuesta = usar(client, 10)

    assert respuesta.json()["alerta_umbral"] is True
    assert notificador.alertas == [("REP-6204", 2)]


def test_el_umbral_se_evalua_sobre_el_disponible_y_no_sobre_el_fisico(client, notificador):
    client.post(
        "/reservas",
        headers=MANTENIMIENTO,
        json={"repuesto_codigo": "REP-6204", "cantidad": 4, "motivo": "Preventivo caldera"},
    )

    respuesta = usar(client, 3)

    assert respuesta.json()["stock_fisico"] == 9
    assert respuesta.json()["stock_disponible"] == 5
    assert respuesta.json()["alerta_umbral"] is True


def test_reservar_tambien_puede_disparar_la_alerta(client, notificador):
    respuesta = client.post(
        "/reservas",
        headers=MANTENIMIENTO,
        json={"repuesto_codigo": "REP-6204", "cantidad": 8, "motivo": "Preventivo caldera"},
    )

    assert respuesta.json()["alerta_umbral"] is True
    assert notificador.alertas == [("REP-6204", 4)]


def test_el_servicio_notifica_sin_pasar_por_http(session, notificador):
    servicio = StockService(session, notificador)

    estado = servicio.registrar_uso("REP-0100", "INC-0002", 1, usuario(Rol.MANTENIMIENTO))

    assert estado.stock_disponible == 2
    assert estado.bajo_umbral is True
    assert notificador.alertas == [("REP-0100", 2)]
