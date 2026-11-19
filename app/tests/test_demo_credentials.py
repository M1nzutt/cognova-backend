from app import cli


def test_demo_password_mismatch_does_not_open_database(monkeypatch, capsys):
    answers = iter(["secret123", "different"])
    monkeypatch.setattr(cli, "getpass", lambda _: next(answers))
    monkeypatch.setattr(
        cli, "Database", lambda _: (_ for _ in ()).throw(AssertionError("opened"))
    )

    assert cli.set_demo_password() == 2
    assert "no coinciden" in capsys.readouterr().err


def test_demo_password_is_hashed_and_never_printed(monkeypatch, capsys):
    user = type("DemoUser", (), {"password_hash": None})()

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def scalar(self, _query):
            return user

        def commit(self):
            pass

    class Database:
        def __init__(self, _settings):
            self.session = lambda: Session()

        def dispose(self):
            pass

    class Passwords:
        def hash(self, value):
            assert value == "secret123"
            return "argon2-hash"

    answers = iter(["secret123", "secret123"])
    monkeypatch.setattr(cli, "getpass", lambda _: next(answers))
    monkeypatch.setattr(cli, "Database", Database)
    monkeypatch.setattr(cli, "Settings", lambda: object())
    monkeypatch.setattr(cli, "PasswordService", Passwords)

    assert cli.set_demo_password() == 0
    output = capsys.readouterr()
    assert "demo.software@example.com" in output.out
    assert "secret123" not in output.out + output.err
    assert user.password_hash == "argon2-hash"
