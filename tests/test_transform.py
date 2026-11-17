from datetime import datetime, timezone

from src.transform import parse_aba_transaction

MSG_DATE = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)


def test_khr_khqr_message():
    text = (
        "៛150,000 paid by SOKHA (*0912) via ABA KHQR (PPCBKHPPXXX). "
        "Remark: payment for goods."
    )
    data = parse_aba_transaction(text, MSG_DATE, shop_name="Mom")

    assert data["currency"] == "KHR"
    assert data["amount"] == 150_000
    assert data["formatted_amount"] == 150_000
    assert data["customer_name"] == "SOKHA"
    assert data["sender_bank"] == "PHNOM PENH COMMERCIAL BANK"
    assert data["remark"] == "payment for goods"
    assert data["shop_name"] == "Mom"
    assert data["date_of_transaction"] == MSG_DATE


def test_usd_aba_pay_message_doubles_to_khr():
    text = "$12 paid by CHHUN SOMBO (*7788) via ABA PAY. Remark: lunch."
    data = parse_aba_transaction(text, MSG_DATE, shop_name="Dad")

    assert data["currency"] == "USD"
    assert data["amount"] == 12
    assert data["formatted_amount"] == 48_000
    assert data["customer_name"] == "CHHUN SOMBO"
    assert data["sender_bank"] == "ABA BANK"
    assert data["remark"] == "lunch"


def test_unknown_bank_code_falls_back_to_code():
    text = "៛50,000 paid by SOMA (*1111) via ABA KHQR (ZZZZZZZZ)."
    data = parse_aba_transaction(text, MSG_DATE)

    assert data["sender_bank"] == "ZZZZZZZZ"


def test_missing_fields_stay_none():
    text = "some unrelated message with no transaction info"
    data = parse_aba_transaction(text, MSG_DATE)

    assert data["currency"] is None
    assert data["amount"] is None
    assert data["customer_name"] is None
    assert data["sender_bank"] is None
    assert data["remark"] is None


def test_amount_with_thousands_separator():
    text = "៛1,250,000 paid by VIN (*2222) via ABA KHQR (PPCBKHPPXXX)."
    data = parse_aba_transaction(text, MSG_DATE)

    assert data["amount"] == 1_250_000
    assert data["formatted_amount"] == 1_250_000
