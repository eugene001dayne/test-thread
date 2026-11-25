from pathlib import Path

from envfile import load_env_file

ROOT = Path(__file__).resolve().parent.parent


def write(tmp_path, text):
    path = tmp_path / ".env"
    path.write_bytes(text.encode("utf-8"))  # bytes: no newline translation on Windows
    return path


def test_reads_simple_pairs(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "A=1\nB=two\n"), env)
    assert env == {"A": "1", "B": "two"}


def test_missing_file_is_fine(tmp_path):
    env = {}
    assert load_env_file(tmp_path / "nope.env", env) == []
    assert env == {}


def test_real_environment_wins_over_the_file(tmp_path):
    env = {"A": "from-shell"}
    names = load_env_file(write(tmp_path, "A=from-file\nB=2\n"), env)
    assert env["A"] == "from-shell"
    assert env["B"] == "2"
    assert names == ["B"]


def test_comments_and_blank_lines_are_skipped(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "# note\n\nA=1\n   \n#B=2\n"), env)
    assert env == {"A": "1"}


def test_matching_quotes_are_stripped(tmp_path):
    env = {}
    load_env_file(write(tmp_path, 'A="hello world"\nB=\'single\'\n'), env)
    assert env == {"A": "hello world", "B": "single"}


def test_value_may_contain_equals_signs(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "A=abc=def==\n"), env)
    assert env["A"] == "abc=def=="


def test_spaces_around_names_and_values_are_trimmed(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "  A = 1  \n"), env)
    assert env == {"A": "1"}


def test_export_prefix_is_accepted(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "export A=1\n"), env)
    assert env == {"A": "1"}


def test_windows_line_endings(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "A=1\r\nB=2\r\n"), env)
    assert env == {"A": "1", "B": "2"}


def test_byte_order_mark_is_ignored(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "\ufeffA=1\n"), env)
    assert env == {"A": "1"}


def test_comment_after_a_value_needs_a_space_before_the_hash(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "A=1 # note\nB=ab#cd\n"), env)
    assert env == {"A": "1", "B": "ab#cd"}


def test_bad_lines_are_skipped(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "justtext\n1BAD=x\nGOOD=y\n"), env)
    assert env == {"GOOD": "y"}


def test_empty_value_is_kept_as_empty_text(tmp_path):
    env = {}
    load_env_file(write(tmp_path, "A=\n"), env)
    assert env == {"A": ""}


def test_returns_names_never_values(tmp_path):
    env = {}
    names = load_env_file(write(tmp_path, "JUDGE_API_KEY=super-secret\n"), env)
    assert names == ["JUDGE_API_KEY"]
    assert "super-secret" not in repr(names)


def test_dotenv_is_git_ignored():
    lines = [line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]
    assert ".env" in lines


def test_example_file_names_the_settings_and_holds_no_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for name in ("JUDGE_PROVIDER", "JUDGE_MODEL", "JUDGE_API_KEY", "JUDGE_BASE_URL", "JUDGE_TIMEOUT"):
        assert name in text
    assert "AIza" not in text
    assert "sk-" not in text