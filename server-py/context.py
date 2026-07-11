# Tracks the last successfully applied command so follow-up corrections like
# "sorry, make it 2 litres" can resolve "it" to an actual item.
# In-memory and single-list scoped — resets on server restart, which is fine
# for this app's scope (one shared list, no multi-user sessions).

_last_command: dict | None = None


def get_last_command() -> dict | None:
    return _last_command


def set_last_command(command: dict) -> None:
    global _last_command
    _last_command = command


def clear_last_command() -> None:
    global _last_command
    _last_command = None