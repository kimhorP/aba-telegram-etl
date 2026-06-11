from src.utils.db import get_connection
from psycopg2.errors import UndefinedTable

def get_last_transaction_date():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT MAX(date_of_transaction) FROM transactions")
        last_date = cursor.fetchone()[0]
    except UndefinedTable:
        last_date = None

    cursor.close()
    conn.close()

    return last_date
