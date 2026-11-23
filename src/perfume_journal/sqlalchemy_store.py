from sqlalchemy.exc import IntegrityError


def matches_integrity_error(
    exc: IntegrityError, expected_sqlstate: str, expected_constraint_name: str
) -> bool:
    driver_error = exc.driver_exception
    sqlstate = getattr(driver_error, "sqlstate", None)
    constraint_name = getattr(driver_error, "constraint_name", None)

    return sqlstate == expected_sqlstate and constraint_name == expected_constraint_name
