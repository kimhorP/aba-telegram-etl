from psycopg2.extras import execute_values
import pandas as pd
from src.utils.db import get_connection

def insert_transactions(df: pd.DataFrame) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO transactions (
            currency,
            amount,
            customer_name,
            date_of_transaction,
            sender_bank,
            remark,
            shop_name,
            formatted_amount
        )
        VALUES %s
    """

    MAX_BIGINT = 9223372036854775807

    data = []
    skipped = []

    for _, row in df.iterrows():
        amt = row.get("amount") if isinstance(row, dict) else row["amount"]

        if pd.isna(amt):
            amt_val = None
        else:
            try:
                amt_val = int(amt)
            except Exception:
                skipped.append((row.to_dict() if hasattr(row, "to_dict") else dict(row), "invalid_int"))
                continue

        if amt_val is not None and abs(amt_val) > MAX_BIGINT:
            skipped.append((row.to_dict() if hasattr(row, "to_dict") else dict(row), f"out_of_range:{amt_val}"))
            continue

        data.append((
            row["currency"],
            amt_val,
            row["customer_name"],
            row["date_of_transaction"],
            row["sender_bank"],
            row["remark"],
            row["shop_name"],
            row.get("formatted_amount"),
        ))

    if skipped:
        print("Warning: skipped rows due to invalid or out-of-range amount:")
        for r, reason in skipped:
            print(reason, r)

    if not data:
        print("No valid rows to insert.")
        cursor.close()
        conn.close()
        return

    try:
        execute_values(cursor, query, data)
        conn.commit()
    except Exception as e:
        print("Batch insert failed, attempting row-by-row to identify problematic row:", e)
        for idx, row in enumerate(data):
            try:
                execute_values(cursor, query, [row])
                conn.commit()
            except Exception as e2:
                print(f"Skipping bad row {idx}: {row} — {e2}")
                conn.rollback()
    finally:
        cursor.close()
        conn.close()
