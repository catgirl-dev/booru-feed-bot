from datetime import datetime, timedelta, timezone


def parse_args(args_str: str):
    """Парсит дату и теги из аргументов команды"""
    if not args_str:
        return None, []

    parts: list[str] = args_str.strip().split()
    try:
        date: datetime = datetime.strptime(parts[0], "%Y-%m-%d")
        tags: list[str] = parts[1:]
    except ValueError:
        date: datetime = datetime.now(timezone(timedelta(hours=-5)))
        tags: list[str] = parts

    return date, tags