import asyncio
from datetime import datetime, date
from rich.console import Console
from rich.prompt import Prompt
from src.utils.telegram_config import get_start_date, get_end_date, cambodia_tz, shops
from src.services.etl import run_etl

console = Console()


def parse_date(prompt_text: str, default: date | None = None) -> datetime:
    while True:
        raw = Prompt.ask(prompt_text, default="").strip()
        if not raw and default is not None:
            d = default
            if isinstance(d, datetime):
                return d
            return datetime(d.year, d.month, d.day, tzinfo=cambodia_tz)
        try:
            parts = raw.split("-")
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return datetime(y, m, d, tzinfo=cambodia_tz)
        except (ValueError, IndexError):
            console.print("[red]Invalid format.[/] Use [bold]YYYY-MM-DD[/] (e.g. 2024-06-01).")


def main():
    while True:
        auto_start = get_start_date()
        auto_end = get_end_date()

        if auto_start is not None:
            answer = Prompt.ask(
                f"Extract from [green]{auto_start.date()}[/] to [green]{auto_end.date()}[/]? (y/n)",
                default="y",
            ).strip().lower()
            if answer == "y":
                start, end = auto_start, auto_end
            else:
                console.print()
                start = parse_date("Start date (YYYY-MM-DD)")
                end = parse_date("End date (YYYY-MM-DD)")
        else:
            console.print("[yellow]No previous data found.[/] Please provide a manual date range.\n")
            start = parse_date("Start date (YYYY-MM-DD)")
            end = parse_date("End date (YYYY-MM-DD)")

        console.print(f"\n[bold]Running ETL[/] from [green]{start.date()}[/] to [green]{end.date()}[/] ...\n")
        result = asyncio.run(run_etl(start, end))
        total = result.get("total_inserted", 0)
        if total:
            console.print(f"[green]Loaded {total} rows into PostgreSQL.[/]")
        for shop, count in result.get("shop_counts", {}).items():
            console.print(f"  {shop}: {count} messages")
        console.print()

        if Prompt.ask("Run again? (y/n)", default="n").strip().lower() != "y":
            break

    console.print("[dim]Done.[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Interrupted.[/]\n")
