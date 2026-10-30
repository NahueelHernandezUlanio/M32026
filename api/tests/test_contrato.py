"""El backend implementa exactamente las operaciones de openapi.yaml, con los mismos códigos de éxito."""

from pathlib import Path

import pytest
import yaml

from app.main import app

CONTRATO = Path(__file__).resolve().parents[2] / "openapi.yaml"
METODOS = {"get", "post", "put", "patch", "delete"}

pytestmark = pytest.mark.skipif(not CONTRATO.exists(), reason="openapi.yaml no está disponible")


def operaciones(paths: dict) -> dict[tuple[str, str], set[str]]:
    return {
        (ruta, metodo): {codigo for codigo in operacion["responses"] if codigo.startswith("2")}
        for ruta, definicion in paths.items()
        for metodo, operacion in definicion.items()
        if metodo in METODOS
    }


@pytest.fixture(scope="module")
def contrato() -> dict[tuple[str, str], set[str]]:
    return operaciones(yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))["paths"])


@pytest.fixture(scope="module")
def implementacion() -> dict[tuple[str, str], set[str]]:
    return operaciones(app.openapi()["paths"])


def test_el_backend_implementa_todas_las_operaciones_del_contrato(contrato, implementacion):
    assert set(contrato) - set(implementacion) == set()


def test_el_backend_no_expone_operaciones_fuera_del_contrato(contrato, implementacion):
    assert set(implementacion) - set(contrato) == set()


def test_los_codigos_de_exito_coinciden(contrato, implementacion):
    diferencias = {op: (contrato[op], implementacion[op]) for op in contrato if contrato[op] != implementacion.get(op)}
    assert diferencias == {}
