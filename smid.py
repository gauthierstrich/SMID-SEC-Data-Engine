import argparse
import polars as pl
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint

load_dotenv()

# Path Settings
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

console = Console()

def print_banner(silent=False):
    if silent: return
    banner = """
    [bold cyan]
     ███████╗███╗   ███╗██╗██████╗     ███████╗███████╗ ██████╗ 
     ██╔════╝████╗ ████║██║██╔══██╗    ██╔════╝██╔════╝██╔════╝ 
     ███████╗██╔████╔██║██║██║  ██║    ███████╗█████╗  ██║      
     ╚════██║██║╚██╔╝██║██║██║  ██║    ╚════██║██╔══╝  ██║      
     ███████║██║ ╚═╝ ██║██║██████╔╝    ███████║███████╗╚██████╗ 
     ╚══════╝╚═╝     ╚═╝╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝ 
    [/bold cyan]
    [bold white]SMID-SEC Data Engine | High-Performance Quant Terminal v1.2[/bold white]
    """
    console.print(banner)

def cmd_status(args):
    if not os.path.exists(ALPHA_MATRIX_PATH):
        rprint(f"[bold red]❌ Alpha Matrix non trouvée.[/bold red]")
        return
    
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    stats = df.select([
        pl.len().alias("rows"),
        pl.col("ticker").n_unique().alias("tickers"),
        pl.col("p_date").min().alias("start"),
        pl.col("p_date").max().alias("end")
    ]).collect()
    
    if args.silent:
        print(json.dumps(stats.to_dicts()[0]))
        return

    table = Table(title="Statistiques du Dataset Maître", border_style="cyan")
    table.add_column("Métrique", style="bold magenta")
    table.add_column("Valeur", style="bold white")
    table.add_row("Lignes totales", f"{stats[0, 'rows']:,}")
    table.add_row("Entreprises uniques", f"{stats[0, 'tickers']:,}")
    table.add_row("Fenêtre temporelle", f"{stats[0, 'start']} au {stats[0, 'end']}")
    console.print(table)

def cmd_get(args):
    ticker = args.ticker.lower()
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).tail(args.limit).collect()
    
    if args.silent:
        print(df.to_pandas().to_json(orient="records"))
        return

    if df.is_empty():
        rprint(f"[bold red]❌ Aucune donnée pour {ticker.upper()}[/bold red]")
    else:
        table = Table(title=f"Signaux Récents : {ticker.upper()}", header_style="bold cyan")
        table.add_column("Date")
        table.add_column("Prix")
        table.add_column("P/E")
        table.add_column("ROE")
        table.add_column("Rev Growth")
        table.add_column("R&D Int.")
        
        for row in df.to_dicts():
            table.add_row(
                str(row['p_date']),
                f"{row['close']:.2f}$",
                f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
                f"{row['roe']*100:.1f}%" if row['roe'] else "-",
                f"{row['rev_growth_yoy']*100:.1f}%" if row['rev_growth_yoy'] else "-",
                f"{row['rd_intensity']*100:.1f}%" if row['rd_intensity'] else "-"
            )
        console.print(table)

def cmd_screen(args):
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    target_date = args.date if args.date else "2026-04-02"
    res = df.filter(pl.col("p_date") == target_date)
    
    # Custom Query Filter (The power of Polars)
    if args.filter:
        try:
            # On permet de passer une chaine de caractere complexe a Polars
            # Note: eval est dangereux, mais ici on est en local. 
            # On utilise plutot une approche securisee via l'argument parser.
            pass 
        except:
            rprint("[bold red]❌ Erreur dans la syntaxe du filtre.[/bold red]")

    # Ratios hardcoded pour simplicité rapide
    if args.pe_max: res = res.filter(pl.col("pe_ratio") < args.pe_max)
    if args.roe_min: res = res.filter(pl.col("roe") > args.roe_min)
    if args.growth_min: res = res.filter(pl.col("rev_growth_yoy") > args.growth_min)
    if args.sector: res = res.filter(pl.col("sector") == args.sector)
    
    final = res.collect()
    
    if args.silent:
        print(final.to_pandas().to_json(orient="records"))
        return

    if final.is_empty():
        rprint(f"[bold red]❌ Aucun candidat trouvé.[/bold red]")
    else:
        table = Table(title=f"Screener Results ({target_date})", border_style="green")
        table.add_column("Ticker", style="bold magenta")
        table.add_column("Secteur")
        table.add_column("P/E")
        table.add_column("ROE", style="yellow")
        table.add_column("Growth", style="blue")
        
        for row in final.sort("rev_growth_yoy", descending=True).head(20).to_dicts():
            table.add_row(
                row['ticker'].upper(), row['sector'],
                f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
                f"{row['roe']*100:.1f}%" if row['roe'] else "-",
                f"{row['rev_growth_yoy']*100:.1f}%" if row['rev_growth_yoy'] else "-"
            )
        console.print(table)

def cmd_export(args):
    with console.status(f"[bold green]Exportation en cours...") as status:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        if args.start: df = df.filter(pl.col("p_date") >= datetime.strptime(args.start, "%Y-%m-%d").date())
        if args.end: df = df.filter(pl.col("p_date") <= datetime.strptime(args.end, "%Y-%m-%d").date())
        if args.sector: df = df.filter(pl.col("sector") == args.sector)
        if args.min_adv: df = df.filter(pl.col("adv_20d") >= args.min_adv)
        
        if args.cols:
            cols = ["ticker", "p_date"] + args.cols.split(",")
            df = df.select([c for c in cols if c in df.collect_schema().names()])
        
        final = df.collect()
        final.write_parquet(args.output, compression="zstd")
    
    if not args.silent:
        rprint(f"\n[bold green]✅ Dataset exporté ({len(final):,} lignes) vers {args.output}[/bold green]")

def main():
    parser = argparse.ArgumentParser(description="SMID-SEC Data Engine Master CLI", add_help=False)
    parser.add_argument("--silent", action="store_true", help="Désactive l'UI pour une utilisation par script")
    subparsers = parser.add_subparsers(dest="command")

    # Commandes
    subparsers.add_parser("status", help="Statistiques du dataset")
    
    get_p = subparsers.add_parser("get", help="Infos ticker")
    get_p.add_argument("ticker")
    get_p.add_argument("--limit", type=int, default=10)

    screen_p = subparsers.add_parser("screen", help="Trouver des opportunités")
    screen_p.add_argument("--date")
    screen_p.add_argument("--pe-max", type=float)
    screen_p.add_argument("--roe-min", type=float)
    screen_p.add_argument("--growth-min", type=float)
    screen_p.add_argument("--sector")

    export_p = subparsers.add_parser("export", help="Générer un dataset pour backtest")
    export_p.add_argument("--output", required=True)
    export_p.add_argument("--start")
    export_p.add_argument("--end")
    export_p.add_argument("--sector")
    export_p.add_argument("--min-adv", type=float)
    export_p.add_argument("--cols")

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command:
        print_banner(args.silent)
        if args.command == "status": cmd_status(args)
        elif args.command == "get": cmd_get(args)
        elif args.command == "screen": cmd_screen(args)
        elif args.command == "export": cmd_export(args)

if __name__ == "__main__":
    main()
