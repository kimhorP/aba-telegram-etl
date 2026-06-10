from telethon import TelegramClient
import pandas as pd
from src.extract import extract_messages
from src.transform import parse_aba_transaction
from src.load import insert_transactions
from src.utils.telegram_config import api_id, api_hash, shops


async def run_etl(start_date, end_date, on_message=None):
    from src.utils.database import ensure_tables
    ensure_tables()

    if not shops:
        print("No shops configured. Set SHOPS in .env (format: name:id,name:id,...).")
        return {"error": "no_shops"}

    client = TelegramClient("session", api_id, api_hash)
    all_rows = []
    shop_counts = {}

    async with client:
        for shop in shops:
            msgs = await extract_messages(
                client, shop["id"], start_date, end_date, on_message
            )
            shop_counts[shop["name"]] = len(msgs)

            transformed = [
                parse_aba_transaction(x["text"], x["date"], shop["name"])
                for x in msgs
            ]
            all_rows.extend(transformed)

    if not all_rows:
        print("No messages found in any shop for the given date range.")
        return {"shop_counts": shop_counts, "total_inserted": 0}

    df = pd.DataFrame(all_rows)
    df = df.rename(columns={"date": "date_of_transaction"})
    df = df[[
        "currency",
        "amount",
        "customer_name",
        "date_of_transaction",
        "sender_bank",
        "remark",
        "shop_name",
        "formatted_amount",
    ]]

    insert_transactions(df)
    return {"shop_counts": shop_counts, "total_inserted": len(df)}
