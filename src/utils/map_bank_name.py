import pandas as pd
import os

_path = os.path.join(os.path.dirname(__file__), "..", "data", "bank_swift_code.csv")
bank_df = pd.read_csv(_path)

bank_df["bank"] = bank_df["bank"].astype(str).str.strip().str.upper()
bank_df["bank_code"] = bank_df["bank_code"].astype(str).str.strip().str.upper()

BANK_CODE_MAP = dict(zip(bank_df["bank_code"], bank_df["bank"]))


def map_bank_name(value: str) -> str | None:
    if not value:
        return None

    value = str(value).strip().upper()

    return BANK_CODE_MAP.get(value, value)
