from src.utils.db import get_connection

def get_last_transaction_date():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(date_of_transaction) FROM transactions")
    last_date = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return last_date
