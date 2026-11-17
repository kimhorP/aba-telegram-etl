from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.extract import extract_messages, is_aba_transaction

TZ = timezone.utc
START = datetime(2025, 1, 1, tzinfo=TZ)

ABA_MSG = (
    "៛150,000 paid by SOKHA (*0912) via ABA KHQR (PPCBKHPPXXX). "
    "Remark: payment for goods."
)


class FakeMsg:
    def __init__(self, date, text):
        self.date = date
        self.text = text


class FakeClient:
    def __init__(self, msgs):
        self._msgs = msgs

    def iter_messages(self, shop_id, reverse=True):
        async def gen():
            for m in self._msgs:
                yield m

        return gen()


def test_is_aba_transaction_accepts_valid_message():
    assert is_aba_transaction(ABA_MSG) is True


def test_is_aba_transaction_rejects_short_text():
    assert is_aba_transaction("$1 paid by X (*1) via ABA") is False


def test_is_aba_transaction_rejects_non_aba_text():
    assert is_aba_transaction("hello world, this is just a normal chat message") is False


def test_is_aba_transaction_rejects_empty():
    assert is_aba_transaction("") is False
    assert is_aba_transaction(None) is False


async def test_throttle_sleeps_every_100_fetched_messages():
    old = [
        FakeMsg(datetime(2024, 6, 1, tzinfo=TZ), "unrelated old chatter")
        for _ in range(250)
    ]
    with patch("src.extract.asyncio.sleep", new_callable=AsyncMock) as sleep:
        out = await extract_messages(FakeClient(old), shop_id=1, start_date=START)

    assert out == []
    assert sleep.await_count == 2
    sleep.assert_awaited_with(1)


async def test_throttle_counts_fetched_not_matched():
    msgs = [FakeMsg(START + timedelta(hours=i), "not an aba message") for i in range(205)]
    msgs.append(FakeMsg(START + timedelta(days=1), ABA_MSG))

    with patch("src.extract.asyncio.sleep", new_callable=AsyncMock) as sleep:
        out = await extract_messages(FakeClient(msgs), shop_id=1, start_date=START)

    assert len(out) == 1
    assert sleep.await_count == 2


async def test_extracts_only_messages_in_range():
    msgs = [
        FakeMsg(datetime(2024, 1, 1, tzinfo=TZ), ABA_MSG),
        FakeMsg(START + timedelta(days=1), ABA_MSG),
        FakeMsg(START + timedelta(days=100), ABA_MSG),
    ]
    with patch("src.extract.asyncio.sleep", new_callable=AsyncMock):
        out = await extract_messages(
            FakeClient(msgs),
            shop_id=1,
            start_date=START,
            end_date=START + timedelta(days=30),
        )

    assert len(out) == 1
    assert out[0]["date"] == START + timedelta(days=1)
