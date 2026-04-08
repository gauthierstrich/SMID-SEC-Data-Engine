import argparse
import polars as pl
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich import print as rprint

load_dotenv()

# Configuration des Chemins
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

console = Console()

def get_header():
    """Barre de statut supérieure style Bloomberg"""
    now = datetime.now().strftime("%d %b %y | %H:%M:%S")
    header = Text()
    header.append(" SQ <GO> ", style="bold black on #0000ff")
    header.append(f"  STRICH QUANT CORE - INSTITUTIONAL TERMINAL ", style="bold white on #333333")
    header.append(f"  {now} ", style="bold white on #555555")
    return header

def print_header():
    rprint(get_header())
    rprint("-" * console.width)

def cmd_status(args):
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    stats = df.select([
        pl.len().alias("rows"),
        pl.col("ticker").n_unique().alias("tickers"),
        pl.col("p_date").min().alias("start"),
        pl.col("p_date").max().alias("end")
    ]).collect()
    
    rprint("\n[bold yellow]SYS-CHECK / DATABASE INTEGRITY[/bold yellow]")
    table = Table(box=None, header_style="bold blue", padding=(0, 2))
    table.add_column("METRIC")
    table.add_column("VALUE")
    
    table.add_row("MASTER_ROWS", f"{stats[0, 'rows']:,}")
    table.add_row("UNIV_SIZE", f"{stats[0, 'tickers']:,} Securities")
    table.add_row("TIME_SPAN", f"{stats[0, 'start']} TO {stats[0, 'end']}")
    table.add_row("STORAGE", LACIE_STORAGE)
    
    console.print(table)

def cmd_des(args):
    ticker = args.ticker.lower()
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).tail(1).collect()
    
    if df.is_empty():
        rprint(f"[bold red]N.A. Equity (No Match for {ticker.upper()})[/bold red]")
        return

    row = df.to_dicts()[0]
    
    rprint(f"\n[bold white on blue] {ticker.upper()} US Equity [/] [bold white] DES - DESCRIPTION[/]")
    rprint(f"[dim]{row['sector']} | {row['industry']}[/dim]\n")

    table = Table(box=None, padding=(0, 4))
    table.add_column("Valuation", style="cyan")
    table.add_column("Value", style="bold white")
    table.add_column("Quality", style="yellow")
    table.add_column("Value ", style="bold white")
    
    table.add_row("Last Price", f"{row['close']:.2f}", "ROE %", f"{row['roe']*100:.1f}%")
    table.add_row("Mkt Cap (M)", f"{row['mkt_cap']/1e6:,.1f}", "ROA %", f"{row['roa']*100:.1f}%")
    table.add_row("P/E (TTM)", f"{row['pe_ratio']:.1f}", "G. Margin", f"{row['gross_margin']*100:.1f}%")
    table.add_row("P/B", f"{row['pb_ratio']:.1f}", "Debt/Eq", f"{row['debt_to_equity']:.2f}")
    
    console.print(table)

def cmd_fa(args):
    ticker = args.ticker.lower()
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).tail(15).collect()
    
    if df.is_empty():
        rprint(f"[bold red]N.A. Financials[/bold red]")
        return

    table = Table(title=f"[bold white]FA - {ticker.upper()} Financial Analysis (Historical PIT)[/bold white]", 
                  box=None, header_style="bold blue")
    table.add_column("DATE")
    table.add_column("PRICE", style="green")
    table.add_column("P/E", style="magenta")
    table.add_column("ROE %", style="yellow")
    table.add_column("GROWTH %", style="cyan")
    table.add_column("R&D %", style="dim")
    
    for row in df.to_dicts():
        table.add_row(
            str(row['p_date']), f"{row['close']:.2f}",
            f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
            f"{row['roe']*100:.1f}%" if row['roe'] else "-",
            f"{row['rev_growth_yoy']*100:+.1f}%" if row['rev_growth_yoy'] else "-",
            f"{row['rd_intensity']*100:.1f}%" if row['rd_intensity'] else "-"
        )
    console.print(table)

def cmd_screen(args):
    target_date = args.date if args.date else "2026-04-02"
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("p_date") == target_date)
    
    if args.query:
        try:
            res = df.filter(eval(args.query))
        except Exception as e:
            rprint(f"[bold red]QUERY ERROR: {e}[/bold red]")
            return
    else:
        res = df
        if args.pe_max: res = res.filter(pl.col("pe_ratio") < args.pe_max)
        if args.roe_min: res = res.filter(pl.col("roe") > args.roe_min)

    final = res.collect()
    
    table = Table(title=f"SCREEN: {len(final)} Matches on {target_date}", box=None, header_style="bold blue")
    table.add_column("TICKER", style="bold white")
    table.add_column("SECTOR", style="dim")
    table.add_column("PRICE", justify="right")
    table.add_column("P/E", justify="right", style="magenta")
    table.add_column("ROE %", justify="right", style="yellow")
    table.add_column("MOM 12M", justify="right", style="cyan")
    
    for row in final.sort("mom_12m", descending=True).head(20).to_dicts():
        table.add_row(
            row['ticker'].upper(), row['sector'], f"{row['close']:.2f}",
            f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
            f"{row['roe']*100:.1f}%" if row['roe'] else "-",
            f"{row['mom_12m']*100:+.1f}%" if row['mom_12m'] else "-"
        )
    console.print(table)

def cmd_export(args):
    rprint(f"[bold blue]SQ-OUT: EXPORTING DATASET...[/bold blue]")
    with console.status("[bold green]Preparing extraction...") as status:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        if args.start: df = df.filter(pl.col("p_date") >= datetime.strptime(args.start, "%Y-%m-%d").date())
        if args.end: df = df.filter(pl.col("p_date") <= datetime.strptime(args.end, "%Y-%m-%d").date())
        if args.query: df = df.filter(eval(args.query))
        if args.cols:
            cols = ["ticker", "p_date"] + args.cols.split(",")
            df = df.select([c for c in cols if c in df.collect_schema().names()])
        
        final = df.collect()
        final.write_parquet(args.output, compression="zstd")
    rprint(f"[bold green]✅ SUCCESS: {len(final):,} lines written to {args.output}[/bold green]")

def main():
    parser = argparse.ArgumentParser(description="STRICH QUANT CORE", add_help=True)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status")
    des_p = subparsers.add_parser("des")
    des_p.add_argument("ticker")
    fa_p = subparsers.add_parser("fa")
    fa_p.add_argument("ticker")
    screen_p = subparsers.add_parser("screen")
    screen_p.add_argument("--date")
    screen_p.add_argument("--query")
    screen_p.add_argument("--pe-max", type=float)
    screen_p.add_argument("--roe-min", type=float)
    export_p = subparsers.add_parser("export")
    export_p.add_argument("--output", required=True)
    export_p.add_argument("--start")
    export_p.add_argument("--end")
    export_p.add_argument("--query")
    export_p.add_argument("--cols")

    if len(sys.argv) == 1:
        print_header()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command:
        print_header()
        if args.command == "status": cmd_status(args)
        elif args.command == "des": cmd_des(args)
        elif args.command == "fa": cmd_fa(args)
        elif args.command == "screen": cmd_screen(args)
        elif args.command == "export": cmd_export(args)

if __name__ == "__main__":
    main()
