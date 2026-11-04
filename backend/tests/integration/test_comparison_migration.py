from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect


def alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(backend_root / "alembic.ini")
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_pairwise_feedback_migration_follows_a04_and_downgrades_cleanly(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration-test.sqlite3'}"
    monkeypatch.setenv("SELECTIQ_DATABASE_URL", database_url)
    config = alembic_config(database_url)
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision("0005_pairwise_feedback")

    assert revision is not None
    assert revision.down_revision == "0004_brief_interpretation"

    command.upgrade(config, "0004_brief_interpretation")
    engine = create_engine(database_url)
    tables_before = set(inspect(engine).get_table_names())
    assert {"photo_features", "brief_interpretations", "guided_scores"} <= tables_before

    command.upgrade(config, "0005_pairwise_feedback")
    assert "comparison_choices" in inspect(engine).get_table_names()

    command.downgrade(config, "0004_brief_interpretation")
    tables_after = set(inspect(engine).get_table_names())
    assert "comparison_choices" not in tables_after
    assert {"photo_features", "brief_interpretations", "guided_scores"} <= tables_after
    engine.dispose()
