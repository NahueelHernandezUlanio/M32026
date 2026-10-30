from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.auth import USUARIOS_STUB, Usuario
from app.db import get_session
from app.main import app
from app.models import Repuesto, Reserva, Rol
from app.notificaciones import get_notificador
from app.seed import sembrar

TOKENS = {usuario.rol: token for token, usuario in USUARIOS_STUB.items()}


@dataclass
class NotificadorFalso:
    alertas: list[tuple[str, int]] = field(default_factory=list)
    liberaciones: list[tuple[str, str]] = field(default_factory=list)

    def alerta_umbral(self, repuesto: Repuesto, stock_disponible: int) -> None:
        self.alertas.append((repuesto.codigo, stock_disponible))

    def reserva_liberada(self, reserva: Reserva, repuesto: Repuesto, autorizada_por: str) -> None:
        self.liberaciones.append((reserva.codigo, autorizada_por))


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", lambda conexion, _: conexion.execute("PRAGMA foreign_keys=ON"))
    SQLModel.metadata.create_all(engine)
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
