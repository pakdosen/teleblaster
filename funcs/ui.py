from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


def show_header() -> None:
    console.print(Panel.fit("TelegramScraper Rebuild v0.1", style="bold cyan"))


def show_main_menu() -> None:
    table = Table(title="Main Menu", show_header=False)
    table.add_column("Code", style="cyan", width=6)
    table.add_column("Action", style="white")
    table.add_row("01", "Login Telegram Account")
    table.add_row("02", "Members Scraper")
    table.add_row("03", "Members Adder")
    table.add_row("04", "Message Broadcast")
    table.add_row("05", "Manage Sessions")
    table.add_row("99", "About")
    table.add_row("00", "Exit")
    console.print(table)


def info(msg: str) -> None:
    console.print(f"[bold cyan]i[/] {msg}")


def success(msg: str) -> None:
    console.print(f"[bold green]+[/] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]![/] {msg}")


def error(msg: str) -> None:
    console.print(f"[bold red]x[/] {msg}")
