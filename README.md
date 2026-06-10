# ABA Transaction ETL

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=fff)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=fff)
![Telethon](https://img.shields.io/badge/Telethon-1.42-26A5E4?logo=telegram&logoColor=fff)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=fff)
![pandas](https://img.shields.io/badge/pandas-3.0-150458?logo=pandas&logoColor=fff)
![uv](https://img.shields.io/badge/uv-0.6-1C1E24?logo=uv&logoColor=fff)

Extract ABA bank transaction notifications from Telegram, parse SMS text into structured data, and load into PostgreSQL.

## Features

- **N-shop support** — Works with any number of Telegram shop groups, configured via a single env var.
- **Telegram extraction** — Pulls ABA KHQR payment messages from all configured shop groups.
- **SMS parsing** — Extracts currency, amount, customer name, sender bank, and remark from ABA notification text using regex.
- **Bank code resolution** — Maps raw bank codes from KHQR payloads to full bank names via a reference CSV.
- **Multi-currency** — Tracks USD and KHR amounts; auto-computes KHR-equivalent for USD amounts at a fixed rate of **1 USD = 4,000 KHR**.
- **Simple prompt** — Auto-detects the date range from the last transaction; asks once to confirm or enter dates manually.

## Requirements

- Python 3.12+
- PostgreSQL database
- Telegram API credentials (api_id, api_hash)
- One or more Telegram group IDs

## Installation

```bash
uv sync
```

## Configuration

Create a `.env` file in the project root:

```
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
SHOPS=Mom:123456789,Dad:987654321
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transactions
DB_USER=postgres
DB_PASSWORD=your_password
```

Credentials reference:

| Variable | Required | Description |
|----------|----------|-------------|
| `API_ID` / `API_HASH` | Yes | Telegram app credentials from [my.telegram.org](https://my.telegram.org) |
| `SHOPS` | Yes | Comma-separated `name:id` pairs — one per Telegram group |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Yes | PostgreSQL connection details |
| `DATABASE_URL` | No | Alternative to individual DB_* vars; takes precedence |

## Usage

### Run the ETL pipeline

```bash
uv run python main.py
```

On first run (no data in the database), you'll be prompted for a date range:

```
No previous data found. Please provide a manual date range.

Start date (YYYY-MM-DD): 2024-06-01
End date (YYYY-MM-DD):   2024-12-31
```

On subsequent runs, the tool auto-detects the range (day after the last transaction through yesterday) and asks:

```
Extract from 2025-01-01 to 2025-06-09? (y/n):
```

Type `y` (default) to accept, or `n` to enter dates manually.

### Date format

All dates use the `YYYY-MM-DD` format.

## How it works

```
Telegram groups  →  extract.py   →  transform.py   →  load.py   →  PostgreSQL
  (Telethon)        (raw msgs)      (regex parse)     (batch insert)
```

1. **Extract** — `src/extract.py` fetches messages from all configured Telegram groups for a date range using Telethon. Rate-limited (sleeps 1s every 100 messages per group).
2. **Transform** — `src/transform.py` parses each ABA notification SMS with regex to extract currency (`៛`/`$`), amount, customer name, sender bank, and remark. Bank codes are resolved via a lookup table in `src/data/bank_swift_code.csv`.
3. **Load** — `src/load.py` inserts rows into PostgreSQL in bulk using `psycopg2.extras.execute_values`. Falls back to row-by-row insertion if a batch fails, reporting the problematic row. The `transactions` table is auto-created if it doesn't exist.

### Database table

The pipeline expects a `transactions` table with this schema:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `currency` | VARCHAR(3) | `USD` or `KHR` |
| `amount` | BIGINT | Transaction amount |
| `customer_name` | VARCHAR | Payer name from SMS |
| `date_of_transaction` | TIMESTAMP | Transaction date |
| `sender_bank` | VARCHAR | Resolved bank name |
| `remark` | VARCHAR | Optional remark field |
| `shop_name` | VARCHAR | Shop name from config (e.g. `Mom`, `Dad`) |
| `formatted_amount` | BIGINT | KHR-equivalent (USD × 4000) |

The table is created automatically on every ETL run if it does not already exist (`src/utils/database.py:ensure_tables`). SQLAlchemy model at `src/models/transaction.py`.

## Project structure

```
├── main.py                  # CLI entry point — date prompt + orchestration
├── src/
│   ├── extract.py           # Telegram message fetching (Telethon)
│   ├── transform.py         # ABA SMS parsing (regex)
│   ├── load.py              # PostgreSQL batch insert (psycopg2)
│   ├── models/
│   │   └── transaction.py   # SQLAlchemy model
│   ├── utils/
│   │   ├── config.py        # DB env vars
│   │   ├── db.py            # psycopg2 connection helper
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── get_last_date.py # Last transaction date query
│   │   ├── map_bank_name.py # Bank code → name lookup
│   │   └── telegram_config.py  # Telegram credentials + date helpers
│   └── data/
│       └── bank_swift_code.csv  # Bank code reference
├── pyproject.toml           # Python dependencies and metadata
└── .env                     # Credentials (gitignored)
```

## Troubleshooting

### "No previous transactions found in DB"

You're running for the first time and there are no records yet. Provide a date range when prompted:

```
Start date (YYYY-MM-DD): 2024-01-01
End date (YYYY-MM-DD):   2024-12-31
```

### Telegram authentication

The first time you run the pipeline, Telethon will prompt for your phone number and the verification code sent to Telegram. The session is saved to `session.session` in the project root for reuse.

### Database connection fails

- Make sure PostgreSQL is running.
- Verify the credentials in `.env` match your database setup.
- The tool uses `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` from `.env`. Optionally set `DATABASE_URL` to override them.

### No messages returned

- Check that the group IDs in `SHOPS` are correct Telegram group/supergroup IDs.
- Verify the selected date range contains messages.
- Run with a wider date range to confirm the groups are accessible.

## Tech stack

- **Python 3.12** — Runtime
- **Telethon** — Telegram client library
- **pandas** — DataFrame operations during transform
- **psycopg2** — PostgreSQL driver with batch insert support
- **SQLAlchemy** — ORM for schema management
- **uv** — Python package manager
