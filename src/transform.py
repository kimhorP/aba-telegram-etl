import re
from datetime import timedelta, timezone
from src.utils.map_bank_name import map_bank_name

CAMBODIA_TZ = timezone(timedelta(hours=7))


def _to_local_naive(msg_date):
    if msg_date is None or msg_date.tzinfo is None:
        return msg_date
    return msg_date.astimezone(CAMBODIA_TZ).replace(tzinfo=None)


def parse_aba_transaction(text: str, msg_date, shop_name: str | None = None) -> dict:
    data = {
        "currency": None,
        "amount": None,
        "customer_name": None,
        "sender_bank": None,
        "date_of_transaction": _to_local_naive(msg_date),
        "remark": None,
        "shop_name": shop_name,
        "formatted_amount": None,
    }

    amount_match = re.search(r'([៛$])\s?([\d,]+)', text)

    if amount_match:
        currency_map = {"៛": "KHR", "$": "USD"}
        data["currency"] = currency_map.get(amount_match.group(1))
        data["amount"] = int(amount_match.group(2).replace(",", ""))
        data["formatted_amount"] = data["amount"] * 4000 if data["currency"] == "USD" else data["amount"]

    customer_match = re.search(r'paid by (.+?) \(\*\d+\)', text)

    if customer_match:
        data["customer_name"] = customer_match.group(1).strip()

    if "VIA ABA PAY" in text.upper():
        data["sender_bank"] = "ABA BANK"
    else:
        khqr_match = re.search(r'via ABA KHQR \((.*?)\)', text)

        if khqr_match:
            raw_bank = khqr_match.group(1).strip()
            data["sender_bank"] = map_bank_name(raw_bank)

    remark_match = re.search(r'Remark:\s*(.*?)\.', text)

    if remark_match:
        data["remark"] = remark_match.group(1).strip()

    return data
