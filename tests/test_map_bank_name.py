from src.utils.map_bank_name import map_bank_name


def test_known_code_maps_to_bank_name():
    assert map_bank_name("PPCBKHPPXXX") == "PHNOM PENH COMMERCIAL BANK"


def test_code_is_case_and_whitespace_insensitive():
    assert map_bank_name("  ppcbkhppxxx ") == "PHNOM PENH COMMERCIAL BANK"


def test_unknown_code_returns_uppercased_input():
    assert map_bank_name("NOTACODE") == "NOTACODE"


def test_empty_string_returns_none():
    assert map_bank_name("") is None


def test_none_returns_none():
    assert map_bank_name(None) is None
