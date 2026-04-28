from app.main import prepare_database


def test_prepare_database_runs_migrations_before_create_tables(monkeypatch):
    calls = []

    def fake_upgrade(config, target):
        calls.append(("upgrade", target, config.config_file_name))

    def fake_create_tables():
        calls.append(("create_tables",))

    monkeypatch.setattr("app.main.command.upgrade", fake_upgrade)
    monkeypatch.setattr("app.main.create_tables", fake_create_tables)

    prepare_database()

    assert calls[0][0] == "upgrade"
    assert calls[0][1] == "head"
    assert calls[0][2].endswith("backend\\alembic.ini")
    assert calls[1] == ("create_tables",)
