import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.models import AlertTriage

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@localhost:5432/infra_ops")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a request-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_service_exists(session: Session, service_name: str) -> bool:
    """Return True if the service exists in valid_services."""
    result = session.execute(
        text("SELECT 1 FROM valid_services WHERE service_name = :name"),
        {"name": service_name},
    ).fetchone()
    return result is not None


def write_triage_log(
    session: Session,
    raw_input: str,
    triage: AlertTriage,
    score: float,
    trace_id: str | None,
) -> None:
    """Persist triage output for auditing and offline analysis."""
    session.execute(
        text(
            """
            INSERT INTO triage_log
                (raw_input, service_name, severity_level, is_db_issue, trust_score, langfuse_trace_id)
            VALUES
                (:raw, :svc, :sev, :db, :score, :trace)
            """
        ),
        {
            "raw": raw_input,
            "svc": triage.service_name,
            "sev": triage.severity_level,
            "db": triage.is_database_issue,
            "score": score,
            "trace": trace_id,
        },
    )
    session.commit()
