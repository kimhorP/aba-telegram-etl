import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from src.utils.get_last_date import get_last_transaction_date

load_dotenv()

cambodia_tz = timezone(timedelta(hours=7))

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

_SHOP_RAW = os.getenv("SHOPS", "")
shops = []
if _SHOP_RAW:
    for pair in _SHOP_RAW.split(","):
        if ":" in pair:
            name, sid = pair.split(":", 1)
            shops.append({"name": name.strip(), "id": int(sid.strip())})


def get_start_date():
    last_date = get_last_transaction_date()
    if last_date is None:
        return None
    return (last_date + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=cambodia_tz
    )


def get_end_date():
    return (datetime.now(cambodia_tz) - timedelta(days=1)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
