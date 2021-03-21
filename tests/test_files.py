from typing import Optional, Tuple, Type, Union

import pytest
from request_file import files


@pytest.mark.parametrize(
    ("line", "key", "value", "error"),
    [
        # Basic
        ("KEY=VALUE", "KEY", "VALUE", None),
        # Leading + trailing spaces
        ("  KEY=VALUE", "KEY", "VALUE", None),
        ("KEY=VALUE  ", "KEY", "VALUE", None),
        # Quoting
        ("KEY='VALUE1'", "KEY", "VALUE1", None),
        ('KEY="VALUE1"', "KEY", "VALUE1", None),
        ("KEY='VALUE1  VALUE2'", "KEY", "VALUE1  VALUE2", None),
        ('KEY="VALUE1  VALUE2"', "KEY", "VALUE1  VALUE2", None),
        # Single line
        ("KEY=VALUE1 ;VALUE2", "KEY", "VALUE1", None),
        # Invalid values
        ("KEY=VALUE1 VALUE2", "", "", ValueError),
        ("KEY =VALUE", "", "", ValueError),
        ("KEY= VALUE", "", "", ValueError),
        ("# Comment", "", "", ValueError),
        ("  # Comment", "", "", ValueError),
        ("#Comment", "", "", ValueError),
    ],
)
def test_read_var(
    line: str, key: str, value: str, error: Union[Type[Exception], None]
) -> None:
    if error is not None:
        try:
            files.read_var(line) == (key, value)
        except Exception as exc:
            assert isinstance(exc, error)
        else:
            assert False, f"should throw a {error.__name__}"
    else:
        assert files.read_var(line) == (key, value)


@pytest.mark.parametrize(("key", "value", "line"), [("KEY", "VALUE", "KEY='VALUE'")])
def test_write_var(key: str, value: str, line: str) -> None:
    assert files.write_var(key, value) == line
