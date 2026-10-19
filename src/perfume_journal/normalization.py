def create_key(value: str | None) -> str | None:
    if value is None:
        return None

    return " ".join(value.split()).casefold()
