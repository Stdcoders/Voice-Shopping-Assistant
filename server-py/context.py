
_last_command: dict | None = None


def get_last_command() -> dict | None:
    return _last_command


def set_last_command(command: dict) -> None:
    global _last_command
    _last_command = command


def clear_last_command() -> None:
    global _last_command
    _last_command = None
