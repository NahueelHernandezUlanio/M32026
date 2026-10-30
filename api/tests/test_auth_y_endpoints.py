"""Auth stub con roles, /health y el resto de los endpoints del contrato."""

from datetime import datetime

import pytest

from app.models import Rol
from app.services import turno_de
from tests.conftest import auth, repuesto


def test_health_es_publico(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_sin_token_devuelve_401(client):
    respuesta = client.get("/repuestos/REP-6204")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_token_desconocido_devuelve_401(client):
    assert client.get("/repuestos/REP-6204", headers={"Authorization": "Bearer inventado"}).status_code == 401


@pytest.mark.parametrize("rol", list(Rol))
def test_auth_me_devuelve_el_rol_del_token(client, rol):
    assert client.get("/auth/me", headers=auth(rol)).json()["rol"] == rol


@pytest.mark.parametrize("rol", [Rol.OPERARIO, Rol.CONSULTA])
def test_operario_y_consulta_no_registran_usos(client, rol):
    respuesta = client.post(
        "/repuestos/REP-6204/usos",
        headers=auth(rol),
        json={"destino_id": "INC-0001", "cantidad": 1},
    )

    assert respuesta.status_code == 403


def test_consulta_puede_ver_repuestos_pero_no_reportar(client):
    assert client.get("/repuestos/REP-6204", headers=auth(Rol.CONSULTA)).status_code == 200
    respuesta = client.post(
        "/incidencias",
        headers=auth(Rol.CONSULTA),
        data={"codigo_maquina": "MAQ-0001", "descripcion": "x"},
    )
    assert respuesta.status_code == 403


def test_operario_reporta_incidencia_con_fotos(client, tmp_path):
    respuesta = client.post(
        "/incidencias",
        headers=auth(Rol.OPERARIO),
        data={"codigo_maquina": "MAQ-0002", "descripcion": "Pierde aceite", "turno": "noche"},
        files=[("fotos", ("foto.jpg", b"\xff\xd8contenido", "image/jpeg"))],
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {"id": "INC-0003", "estado": "REPORTADA"}
    assert len(list((tmp_path / "incidencias").iterdir())) == 1


def test_incidencia_con_maquina_inexistente_devuelve_404(client):
    respuesta = client.post(
        "/incidencias",
        headers=auth(Rol.OPERARIO),
        data={"codigo_maquina": "MAQ-9999", "descripcion": "x"},
    )

    assert respuesta.status_code == 404


def test_una_incidencia_reportada_pasa_a_reparacion_y_es_destino_de_uso(client):
    nueva = client.post(
        "/incidencias",
        headers=auth(Rol.OPERARIO),
        data={"codigo_maquina": "MAQ-0003", "descripcion": "Banda desalineada"},
    ).json()

    respuesta = client.post(f"/incidencias/{nueva['id']}/reparacion", headers=auth(Rol.MANTENIMIENTO))

    assert respuesta.json()["estado"] == "EN_REPARACION"
    destinos = client.get("/destinos-uso", headers=auth(Rol.MANTENIMIENTO)).json()
    assert {"id": nueva["id"], "maquina": "Banda 3"} in destinos


@pytest.mark.parametrize(
    ("hora_utc", "turno"),
    [("2026-10-30T10:00:00+00:00", "manana"), ("2026-10-30T18:00:00+00:00", "tarde"), ("2026-10-30T03:00:00+00:00", "noche")],
)
def test_el_turno_se_deriva_del_timestamp_en_hora_de_planta(hora_utc, turno):
    assert turno_de(datetime.fromisoformat(hora_utc)) == turno


def test_rn08_recepcion_carga_stock_lote_y_ubicacion(client, session, tmp_path):
    respuesta = client.post(
        "/repuestos/REP-6204/recepciones",
        headers=auth(Rol.ENCARGADO),
        data={"lote": "L-2026-045", "cantidad": "5", "ubicacion": "B-01-04"},
        files={"remito": ("remito.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["stock_fisico"] == 17
    rodamiento = repuesto(session)
    assert (rodamiento.lote, rodamiento.ubicacion_codigo) == ("L-2026-045", "B-01-04")
    assert len(list((tmp_path / "remitos").iterdir())) == 1


def test_rn08_ubicacion_inexistente_devuelve_404(client):
    respuesta = client.post(
        "/repuestos/REP-6204/recepciones",
        headers=auth(Rol.ENCARGADO),
        data={"lote": "L-1", "cantidad": "1", "ubicacion": "Z-99-99"},
    )

    assert respuesta.status_code == 404


def test_ubicaciones(client):
    assert client.get("/ubicaciones", headers=auth(Rol.MANTENIMIENTO)).json() == ["A-03-12", "A-03-13", "B-01-04"]
