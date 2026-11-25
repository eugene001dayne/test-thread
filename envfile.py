import re

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_TRAILING_COMMENT = re.compile(r"\s#")


def _clean_value(raw):
    value = raw.strip()
    if value and value[0] in "\"'":
        end = value.find(value[0], 1)
        if end != -1:
            return value[1:end]
    match = _TRAILING_COMMENT.search(value)
    if match:
        value = value[: match.start()]
    return value.strip()


def load_env_file(path, env):
    """Load NAME=value lines into env without overriding anything already set.

    Returns the names that were loaded (never the values).
    """
    try:
        with open(path, encoding="utf-8-sig") as handle:  # utf-8-sig drops Notepad's invisible marker
            text = handle.read()
    except FileNotFoundError:
        return []

    loaded = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        name, separator, raw = line.partition("=")
        name = name.strip()
        if not separator or not _NAME.match(name):
            continue
        if name in env:
            continue
        env[name] = _clean_value(raw)
        loaded.append(name)
    return loaded