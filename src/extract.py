import re
from datetime import datetime
import asyncio
from collections.abc import Callable

_ABA_PATTERN = re.compile(
    r'[៛$]\s?[\d,]+.*paid by .+ \(\*\d+\).*via ABA',
    re.DOTALL
)


def is_aba_transaction(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < 30:
        return False
    return bool(_ABA_PATTERN.search(stripped))


async def extract_messages(
    client,
    shop_id: int,
    start_date: datetime,
    end_date: datetime | None = None,
    on_message: Callable[[], None] | None = None,
):
    messages = []
    count = 0

    async for msg in client.iter_messages(
        shop_id,
        reverse=True
    ):
        if msg.date < start_date:
            continue

        if end_date and msg.date > end_date:
            break

        if not msg.text:
            continue

        if not is_aba_transaction(msg.text):
            continue

        messages.append({
            "date": msg.date,
            "text": msg.text
        })

        count += 1

        if on_message:
            on_message()

        if count % 100 == 0:
            await asyncio.sleep(1)

    return messages
