import os
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, make_url, text
from sqlmodel import Session, SQLModel, create_engine, select

from app.auth import USUARIOS_STUB, Usuario
from app.db import get_session
from app.main import app
from app.models import Repuesto, Reserva, Rol
from app.notificaciones import get_notificador
from app.seed import sembrar

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://planta:planta@localhost:5432/planta_test"
)
TOKENS = {usuario.rol: token for token, usuario in USUARIOS_STUB.items()}


@dataclass
class NotificadorFalso:
    alertas: list[tuple[str, int]] = field(default_factory=list)
    liberaciones: list[tuple[str, str]] = field(default_factory=list)

    def alerta_umbral(self, repuesto: Repuesto, stock_disponible: int) -> None:
        self.alertas.append((repuesto.codigo, stock_disponible))

    def reserva_liberada(self, reserva: Reserva, repuesto: Repuesto, autorizada_por: str) -> None:
        self.liberaciones.append((reserva.codigo, autorizada_por))


def _crear_base_si_no_existe(url: URL) -> None:
    servidor = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with servidor.connect() as conexion:
        existe = conexion.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :nombre"), {"nombre": url.database}
        ).scalar()
        if not existe:
            conexion.execute(text(f'CREATE DATABASE "{url.database}"'))
    servidor.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_url(TEST_DATABASE_URL)
    _crear_base_si_no_existe(url)
    engine = create_engine(url)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Cada test arranca con las tablas vacías, los ids reiniciados y el seed cargado."""
    tablas = ", ".join(f'"{tabla.name}"' for tabla in SQLModel.metadata.sorted_tables)
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
    with Session(engine) as session:
        sembrar(session)
        yield session


@pytest.fixture
def notificador() -> NotificadorFalso:
    return NotificadorFalso()


@pytest.fixture
def client(session: Session, notificador: NotificadorFalso, tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setattr("app.almacenamiento.UPLOAD_DIR", tmp_path)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_notificador] = lambda: notificador
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def auth(rol: Rol) -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKENS[rol]}"}


def usuario(rol: Rol) -> Usuario:
    return USUARIOS_STUB[TOKENS[rol]]


def repuesto(session: Session, codigo: str = "REP-6204") -> Repuesto:
    session.expire_all()
    return session.exec(select(Repuesto).where(Repuesto.codigo == codigo)).one()
