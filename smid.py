import argparse
import polars as pl
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

load_dotenv()

# Path Settings
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

console = Console()

def print_banner():
    banner = """
    [bold cyan]
     ███████╗███╗   ███╗██╗██████╗     ███████╗███████╗ ██████╗ 
     ██╔════╝████╗ ████║██║██╔══██╗    ██╔════╝██╔════╝██╔════╝ 
     ███████╗██╔████╔██║██║██║  ██║    ███████╗█████╗  ██║      
     ╚════██║██║╚██╔╝██║██║██║  ██║    ╚════██║██╔══╝  ██║      
     ███████║██║ ╚═╝ ██║██║██████╔╝    ███████║███████╗╚██████╗ 
     ╚══════╝╚═╝     ╚═╝╚═╝╚═════╝     ╚══════╝╚══════╝ ╚═════╝ 
    [/bold cyan]
    [bold white]SMID-SEC Data Engine | Institutional Quant Terminal v1.1[/bold white]
    """
    console.print(banner)

def cmd_status(args):
    rprint("\n[bold yellow]🔍 DIAGNOSTIC SYSTÈME[/bold yellow]")
    if not os.path.exists(ALPHA_MATRIX_PATH):
        rprint(f"[bold red]❌ Alpha Matrix non trouvée : {ALPHA_MATRIX_PATH}[/bold red]")
        return
    
    with console.status("[bold green]Analyse du dataset...") as status:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        stats = df.select([
            pl.len().alias("rows"),
            pl.col("ticker").n_unique().alias("tickers"),
            pl.col("p_date").min().alias("start"),
            pl.col("p_date").max().alias("end")
        ]).collect()
    
    table = Table(title="Statistiques du Dataset", border_style="cyan")
    table.add_column("Métrique", style="bold magenta")
    table.add_column("Valeur", style="bold white")
    
    table.add_row("Lignes totales", f"{stats[0, 'rows']:,}")
    table.add_row("Entreprises uniques", f"{stats[0, 'tickers']:,}")
    table.add_row("Période historique", f"{stats[0, 'start']} au {stats[0, 'end']}")
    table.add_row("Emplacement", ALPHA_MATRIX_PATH)
    
    console.print(table)

def cmd_get(args):
    ticker = args.ticker.lower()
    rprint(f"\n[bold yellow]🔍 RÉCUPÉRATION : {ticker.upper()}[/bold yellow]")
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).tail(10).collect()
    if df.is_empty():
        rprint(f"[bold red]❌ Aucune donnée trouvée pour {ticker.upper()}[/bold red]")
    else:
        table = Table(title=f"Derniers signaux : {ticker.upper()}", box=None, header_style="bold cyan")
        table.add_column("Date", justify="center")
        table.add_column("Prix", style="bold green")
        table.add_column("P/E", style="magenta")
        table.add_column("ROE", style="yellow")
        table.add_column("Mom 12M", style="blue")
        for row in df.to_dicts():
            table.add_row(str(row['p_date']), f"{row['close']:.2f}$", f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-", f"{row['roe']*100:.1f}%" if row['roe'] else "-", f"{row['mom_12m']*100:.1f}%" if row['mom_12m'] else "-")
        console.print(table)

def cmd_screen(args):
    rprint(f"\n[bold yellow]🎯 FILTRAGE STRATÉGIQUE[/bold yellow]")
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    target_date = args.date if args.date else "2026-04-02"
    res = df.filter(pl.col("p_date") == target_date)
    if args.pe_max: res = res.filter(pl.col("pe_ratio") < args.pe_max)
    if args.roe_min: res = res.filter(pl.col("roe") > args.roe_min)
    if args.mom_min: res = res.filter(pl.col("mom_12m") > args.mom_min)
    if args.sector: res = res.filter(pl.col("sector") == args.sector)
    final = res.select(["ticker", "sector", "close", "pe_ratio", "roe", "mom_12m"]).collect()
    if final.is_empty():
        rprint(f"[bold red]❌ Aucun candidat pour le {target_date}.[/bold red]")
    else:
        table = Table(title=f"Top Candidats ({target_date})", border_style="green")
        table.add_column("Ticker", style="bold magenta")
        table.add_column("Secteur")
        table.add_column("Prix", style="bold green")
        table.add_column("P/E", justify="right")
        table.add_column("ROE", justify="right", style="yellow")
        table.add_column("Mom 12M", justify="right", style="blue")
        for row in final.sort("mom_12m", descending=True).head(20).to_dicts():
            table.add_row(row['ticker'].upper(), row['sector'], f"{row['close']:.2f}$", f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-", f"{row['roe']*100:.1f}%" if row['roe'] else "-", f"{row['mom_12m']*100:.1f}%" if row['mom_12m'] else "-")
        console.print(table)

def cmd_export(args):
    rprint(f"\n[bold magenta]📥 EXPORTATION POUR BACKTEST[/bold magenta]")
    
    if not args.output:
        rprint("[bold red]❌ Erreur : Vous devez spécifier un fichier de sortie avec --output (ex: my_backtest.parquet)[/bold red]")
        return

    with console.status(f"[bold green]Préparation de l'exportation vers {args.output}...") as status:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        
        # Filtres temporels
        if args.start: df = df.filter(pl.col("p_date") >= datetime.strptime(args.start, "%Y-%m-%d").date())
        if args.end: df = df.filter(pl.col("p_date") <= datetime.strptime(args.end, "%Y-%m-%d").date())
        
        # Filtres d'Univers
        if args.sector: df = df.filter(pl.col("sector") == args.sector)
        if args.min_adv: df = df.filter(pl.col("adv_20d") >= args.min_adv)
        
        # Sélection de colonnes
        if args.cols:
            cols = ["ticker", "p_date"] + args.cols.split(",")
            # Ensure unique cols and existence
            df = df.select([c for c in cols if c in df.collect_schema().names()])
        
        # Exécution
        final = df.collect()
        final.write_parquet(args.output, compression="zstd")
    
    rprint(f"\n[bold green]✅ Exportation réussie ![/bold green]")
    rprint(f"   - Fichier : [bold cyan]{args.output}[/bold cyan]")
    rprint(f"   - Volume  : {len(final):,} lignes exportées.")
    rprint(f"   - Colonnes: {final.columns}")

def main():
    parser = argparse.ArgumentParser(
        description="SMID-SEC Data Engine CLI: Une infrastructure de recherche quantitative institutionnelle pour le backtesting de stratégies boursières sans biais et sans triche.",
        add_help=False
    )
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Status Command
    status_p = subparsers.add_parser("status", help="Analyse de santé du dataset")
    status_p.description = "Affiche les statistiques vitales de la matrice Alpha (lignes, tickers, couverture temporelle) et valide l'accessibilité du stockage LaCie."

    # Get Command
    get_p = subparsers.add_parser("get", help="Exploration granulaire d'un ticker")
    get_p.description = "Récupère les 10 dernières journées de cotation enrichies pour un ticker spécifique. Affiche les prix, P/E, ROE et Momentum."
    get_p.add_argument("ticker", help="Le symbole boursier à analyser (ex: AAPL, TSLA, NVDA).")

    # Screen Command
    screen_p = subparsers.add_parser("screen", help="Screener multi-facteurs (Point-in-Time)")
    screen_p.description = "Filtre l'intégralité du marché américain à une date précise du passé selon vos critères Alpha. Utile pour la génération d'hypothèses de trading."
    screen_p.add_argument("--date", help="Date cible au format YYYY-MM-DD. Par défaut: dernière date connue (2026-04-02).")
    screen_p.add_argument("--pe-max", type=float, help="P/E Ratio maximum autorisé (Valorisation).")
    screen_p.add_argument("--roe-min", type=float, help="Return on Equity minimum (Qualité). ex: 0.20 pour 20%%.")
    screen_p.add_argument("--mom-min", type=float, help="Momentum 12 mois minimum (Tendance). ex: 0.10 pour +10%%.")
    screen_p.add_argument("--sector", help="Limiter la recherche à un secteur SEC (ex: Technology, Healthcare).")

    # Export Command
    export_p = subparsers.add_parser("export", help="Générateur de dataset pour Backtest")
    export_p.description = "Extrait et compresse un sous-ensemble de données pour vos scripts de backtest. Élimine les colonnes inutiles pour maximiser la vitesse de vos simulations."
    export_p.add_argument("--output", required=True, help="Chemin complet du fichier .parquet de sortie (ex: strategies/value_test.parquet).")
    export_p.add_argument("--start", help="Date de début de l'extraction (YYYY-MM-DD).")
    export_p.add_argument("--end", help="Date de fin de l'extraction (YYYY-MM-DD).")
    export_p.add_argument("--sector", help="Filtrer par secteur pour réduire la taille du fichier.")
    export_p.add_argument("--min-adv", type=float, help="Seuil de liquidité (ADV 20j en dollars). Exclut les penny stocks illiquides.")
    export_p.add_argument("--cols", help="Liste des signaux Alpha à inclure, séparés par des virgules (ex: pe_ratio,roe,mom_12m).")

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command:
        print_banner()
        if args.command == "status": cmd_status(args)
        elif args.command == "get": cmd_get(args)
        elif args.command == "screen": cmd_screen(args)
        elif args.command == "export": cmd_export(args)

if __name__ == "__main__":
    main()
