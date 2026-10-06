from sqlalchemy import text


def test_readiness_checks_real_postgresql_and_alembic(client, database):
    assert client.get("/api/v1/ready").json() == {"status": "ready"}
    with database.session() as session:
        session.execute(text("UPDATE alembic_version SET version_num = 'outdated'"))
        session.commit()
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
