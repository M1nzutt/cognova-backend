from sqlalchemy import text

from app.services.readiness_service import ReadinessService


def test_readiness_checks_real_postgresql_and_alembic(client, database):
    with database.session() as session:
        revisions = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()
    assert revisions == [ReadinessService.expected_revision]
    assert client.get("/api/v1/ready").json() == {"status": "ready"}
    with database.session() as session:
        session.execute(text("UPDATE alembic_version SET version_num = 'outdated'"))
        session.commit()
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
