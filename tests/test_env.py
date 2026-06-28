"""The cross-platform .env loader."""

from __future__ import annotations

from murbo.env import load_dotenv


def test_load_dotenv_sets_keys_and_respects_quotes_and_export(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# a comment\n"
        "\n"
        "ANTHROPIC_API_KEY=sk-plain\n"
        'MINIMAX_API_KEY="sk-quoted"\n'
        "export OPENAI_API_KEY='sk-exported'\n"
    )
    for k in ("ANTHROPIC_API_KEY", "MINIMAX_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    assert load_dotenv(env) is True
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-plain"
    assert os.environ["MINIMAX_API_KEY"] == "sk-quoted"
    assert os.environ["OPENAI_API_KEY"] == "sk-exported"


def test_load_dotenv_does_not_clobber_real_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("MINIMAX_API_KEY=from-file\n")
    monkeypatch.setenv("MINIMAX_API_KEY", "from-shell")

    load_dotenv(env)
    import os

    assert os.environ["MINIMAX_API_KEY"] == "from-shell"  # exported value wins


def test_load_dotenv_missing_file_is_noop():
    assert load_dotenv("/no/such/.env") is False
