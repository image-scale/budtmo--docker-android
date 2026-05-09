import logging
import os

logger = logging.getLogger(__name__)


def str_to_bool(value: str) -> bool:
    """Convert a string value to a boolean.

    Truthy values: "true", "yes", "t", "1" (case-insensitive)
    Everything else (including empty/None) returns False.

    Raises AttributeError if value is not a string (e.g., bool or int).
    """
    if value is None or value == "":
        logger.info(f"'{value}' is empty!")
        return False

    if not isinstance(value, str):
        raise AttributeError("Expected string input")

    return value.lower() in ("true", "yes", "t", "1")


def require_env(key: str) -> str:
    """Get a required environment variable value.

    Raises RuntimeError if the variable is missing or contains only whitespace.
    """
    try:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"'{key}' is missing.")
        if value.isspace():
            raise RuntimeError(f"'{key}' contains only white space.")
        return value
    except TypeError as err:
        logger.error(err)
        raise


def create_symlink(source: str, target: str) -> None:
    """Create a symbolic link at target pointing to source.

    If target already exists, it will be replaced.
    If source doesn't exist, a dangling symlink is created.
    """
    try:
        os.symlink(source, target)
    except FileNotFoundError as err:
        logger.error(err)
    except FileExistsError:
        os.remove(target)
        os.symlink(source, target)
