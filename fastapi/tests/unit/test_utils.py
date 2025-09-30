import pytest

import app.utils as utils


@pytest.mark.parametrize(
    "input_char, expected",
    [
        ("가", "ㄱ"),
        ("나", "ㄴ"),
        ("다", "ㄷ"),
        ("빠", "ㅃ"),
        ("싸", "ㅆ"),
        ("짜", "ㅉ"),
        ("각", "ㄱ"),
        ("앙", "ㅇ"),
        ("와", "ㅇ"),
        ("힝", "ㅎ"),
        ("힣", "ㅎ"),
        ("부침개", "ㅂㅊㄱ"),
        ("꼭두각시", "ㄲㄷㄱㅅ"),
    ],
)
def test_extract_first_consonant(input_char, expected):
    assert utils.extract_initial_consonant(input_char) == expected


@pytest.mark.parametrize(
    "input_char, expected",
    [
        ("가", True),
        ("힣", True),
        ("A", False),
        ("1", False),
        (" ", False),
        ("!", False),
        ("ㄱ", False),  # Consonant only
        ("ㅏ", False),  # Vowel only
    ],
)
def test_is_hangul_char(input_char, expected):
    assert utils.is_hangul_char(input_char) == expected


@pytest.mark.parametrize(
    "input_string, expected",
    [
        ("안녕", True),
        ("가나다", True),
        ("Hello", False),
        ("가A", False),
        ("가1", False),
        ("가!", False),
        ("", False),
        ("ㄱㄴ", False),
    ],
)
def test_is_hangul_string(input_string, expected):
    assert utils.is_hangul_string(input_string) == expected
