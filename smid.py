#!/usr/bin/env python3
"""
SMID-SEC Data Engine | Institutional Research Terminal v3.0
Outil CLI sécurisé, optimisé (Polars Lazy API) et rigoureux.
Designé pour l'analyse fondamentale et quantitative approfondie.
"""

import argparse
import os
import sys
import json
from datetime import datetime, date
from pathlib import Path

import polars as pl
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.text import Text
from rich import print as rprint
from rich.box import ROUNDED, HEAVY_EDGE

load_dotenv()

# --- CONFIGURATION DYNAMIQUE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Si aucune variable d'environnement n'est définie, on cherche un dossier 'storage' à la racine
DEFAULT_STORAGE = os.path.join(BASE_DIR, "storage")
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", DEFAULT_STORAGE)

# Construction des chemins relatifs aux données Silver
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")
FUND_PATH = os.path.join(LACIE_STORAGE, "silver/fundamentals_master.parquet")

console = Console()


def check_paths() -> bool:
    """Vérifie que les bases de données nécessaires existent."""
    missing = []
    if not os.path.exists(ALPHA_MATRIX_PATH):
        missing.append(ALPHA_MATRIX_PATH)
    if not os.path.exists(FUND_PATH):
        missing.append(FUND_PATH)
    
    if missing:
        rprint("[bold red]❌ Erreur critique : Fichiers de base de données introuvables.[/bold red]")
        for m in missing:
            rprint(f"  - {m}")
        rprint("\n[yellow]💡 Vérifiez que le disque dur est branché ou ajustez LACIE_STORAGE_PATH dans le fichier .env[/yellow]")
        return False
    return True


# --- UTILITAIRES DE FORMATAGE ---
def format_val(val: float) -> str:
    if val is None: return "-"
    if abs(val) >= 1e9: return f"{val/1e9:.2f}B"
    if abs(val) >= 1e6: return f"{val/1e6:.2f}M"
    if abs(val) >= 1e3: return f"{val/1e3:.2f}K"
    return f"{val:.2f}"


def format_pct(val: float) -> str:
    if val is None: return "-"
    color = "green" if val >= 0 else "red"
    return f"[{color}]{val*100:+.1f}%[/{color}]"


def print_banner(silent: bool = False):
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
    [bold white]SMID-SEC Data Engine | Institutional Research Terminal v3.0[/bold white]
    """
    console.print(banner)


# --- COMMANDES CLI ---

def cmd_status(args: argparse.Namespace):
    """Dashboard moderne affichant l'état de santé et les statistiques du moteur."""
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    
    with console.status("[bold blue]Analyse de la Matrice Alpha en cours...") as status:
        try:
            stats = df.select([
                pl.len().alias("rows"),
                pl.col("ticker").n_unique().alias("tickers"),
                pl.col("p_date").min().alias("start"),
                pl.col("p_date").max().alias("end"),
                pl.col("sector").n_unique().alias("sectors")
            ]).collect()
            
            file_size_gb = os.path.getsize(ALPHA_MATRIX_PATH) / (1024**3)
            
        except Exception as e:
            rprint(f"[bold red]❌ Erreur de lecture : {e}[/bold red]")
            sys.exit(1)
        
    if args.silent:
        print(json.dumps(stats.to_dicts()[0], default=str))
        return

    p1 = Panel(Text.assemble((f"{stats[0, 'rows']:,}\n", "bold cyan"), ("Points de données totaux", "dim")), title="[bold]VOLUME[/]", border_style="cyan")
    p2 = Panel(Text.assemble((f"{stats[0, 'tickers']:,}\n", "bold green"), ("Entreprises uniques", "dim")), title="[bold]UNIVERS[/]", border_style="green")
    p3 = Panel(Text.assemble((f"{stats[0, 'start']}\n", "bold yellow"), ("au ", "dim"), (f"{stats[0, 'end']}", "bold yellow")), title="[bold]HISTORIQUE[/]", border_style="yellow")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold magenta]Secteurs couverts[/]", f"[white]{stats[0, 'sectors']}[/]")
    table.add_row("[bold magenta]Poids sur disque[/]", f"[white]{file_size_gb:.2f} GB[/]")
    table.add_row("[bold magenta]Format stockage[/]", "[white]Apache Parquet (Zstd)[/]")
    table.add_row("[bold magenta]Type de données[/]", "[white]Point-in-Time (Pit)[/]")
    
    console.print("\n")
    console.print(Columns([p1, p2, p3], equal=True, expand=True))
    console.print(Panel(table, title="[bold white]PROPRIÉTÉS DU MOTEUR[/]", border_style="magenta"))
    
    schema = df.collect_schema().names()
    columns_text = Text(", ".join(schema), style="dim italic white")
    console.print(Panel(columns_text, title="[bold]COLONNES ALPHA DISPONIBLES[/]", border_style="white", padding=(1, 2)))


def cmd_terminal(args: argparse.Namespace):
    """TERMINAL PROFESSIONNEL - Analyse complète d'une entreprise (Fondamentaux + Valorisation)."""
    ticker = args.ticker.lower()
    
    with console.status(f"[bold blue]Récupération des données pour {ticker.upper()}...[/bold blue]"):
        try:
            # 1. Charger toutes les données Alpha pour ce ticker
            df_alpha = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).collect()
            
            if df_alpha.is_empty():
                rprint(f"[bold red]❌ Ticker {ticker.upper()} non trouvé.[/bold red]")
                return

            # 2. Charger les fondamentaux bruts (pour avoir les trimestres réels vs TTM)
            cik = df_alpha[0, "cik"]
            df_f = pl.scan_parquet(FUND_PATH).filter(pl.col("cik") == cik).collect()
            
            # 3. Préparer les données
            latest = df_alpha.tail(1).to_dicts()[0]
            
            # Stats actuelles pour le header
            mkt_cap = latest.get("mkt_cap") or 0
            price = latest.get("close") or 0
            sector = latest.get("sector", "N/A")
            industry = latest.get("industry", "N/A")
            pe_curr = latest.get("pe_ratio") or 0
            pb_curr = latest.get("pb_ratio") or 0
            roe_curr = latest.get("roe") or 0
            
        except Exception as e:
            rprint(f"[bold red]❌ Erreur lors de l'analyse : {e}[/bold red]")
            import traceback
            traceback.print_exc()
            return

    # --- CONSTRUCTION DU HEADER ---
    header_text = Text.assemble(
        (f" {ticker.upper()} ", "bold black on cyan"),
        (f" | {sector} | {industry} ", "dim italic"),
        ("\n"),
        (f" Prix: ${price:.2f} ", "bold white"),
        (f" | Market Cap: ${format_val(mkt_cap)} ", "cyan"),
        (f" | P/E: {pe_curr:.1f} ", "yellow"),
        (f" | ROE: {(roe_curr*100) if roe_curr else 0:.1f}% ", "green")
    )
    console.print(Panel(header_text, border_style="cyan", box=HEAVY_EDGE))

    # --- SECTION 1: PERFORMANCE FINANCIÈRE (P&L) ---
    # On pivote les fondamentaux pour l'historique trimestriel/annuel
    tags_to_show = ["revenue", "net_income", "operating_income", "gross_margin", "shares_outstanding"]
    
    # Préparer une version simplifiée de la matrice alpha pour les jointures de PER
    df_alpha_mini = df_alpha.select(["p_date", "pe_ratio", "pb_ratio", "mkt_cap", "close"])

    def get_hist_table(is_annual=True):
        period_label = "ANNUEL" if is_annual else "TRIMESTRIEL"
        limit = 10 if is_annual else 24
        
        # Filtrer et pivoter
        df_p = df_f.filter(
            (pl.col("is_fy") == is_annual) & 
            (pl.col("tag").is_in(tags_to_show))
        ).pivot(values="val", index="end_date", on="tag", aggregate_function="last").sort("end_date", descending=True)
        
        if df_p.is_empty(): return Panel(f"Aucune donnée {period_label.lower()} disponible", title=period_label)

        # Convertir end_date en date pour la jointure
        df_p = df_p.with_columns(pl.col("end_date").str.to_date("%Y-%m-%d").alias("p_date"))
        
        # Joindre avec la matrice alpha pour avoir le PER à la date de clôture
        # Note: join_asof permet de trouver la date de marché la plus proche si la clôture est un weekend
        df_p = df_p.sort("p_date")
        df_alpha_sorted = df_alpha_mini.sort("p_date")
        
        df_final = df_p.join_asof(
            df_alpha_sorted, 
            on="p_date", 
            strategy="backward"
        ).sort("p_date", descending=True).head(limit)

        table = Table(title=f"PROFIL DE PERFORMANCE & VALORISATION - {period_label}", box=ROUNDED, header_style="bold magenta", expand=True)
        table.add_column("Date", style="dim")
        table.add_column("Revenue", justify="right")
        table.add_column("Net Income", justify="right")
        table.add_column("Margin %", justify="right")
        table.add_column("Growth YoY", justify="right")
        table.add_column("PER", style="bold yellow", justify="right")
        table.add_column("P/B", justify="right")
        table.add_column("Prix", justify="right")

        # Calculer croissance pour le tableau
        df_final = df_final.with_columns([
            (pl.col("revenue").shift(-1)).alias("rev_prev")
        ])
        
        for row in df_final.to_dicts():
            rev = row.get("revenue")
            ni = row.get("net_income")
            rev_prev = row.get("rev_prev")
            pe = row.get("pe_ratio")
            pb = row.get("pb_ratio")
            px = row.get("close")
            
            margin = (ni / rev) if rev and ni else 0
            growth = (rev / rev_prev - 1) if rev and rev_prev else 0
            
            table.add_row(
                str(row["p_date"]),
                format_val(rev),
                format_val(ni),
                f"{margin*100:.1f}%",
                format_pct(growth),
                f"{pe:.1f}" if pe else "-",
                f"{pb:.2f}" if pb else "-",
                f"${px:.2f}" if px else "-"
            )
        return table

    # --- SECTION 2: VALORISATION & MULTIPLES ---
    def get_valuation_table():
        # On échantillonne la matrice alpha à chaque fin de trimestre pour voir l'évolution du PER
        # On prend une date par trimestre (ex: le 15 du mois de fin de trimestre ou plus proche)
        # Pour simplifier, on prend les points mensuels de la matrice alpha
        df_val = df_alpha.with_columns(
            pl.col("p_date").dt.truncate("1mo").alias("month")
        ).group_by("month").agg([
            pl.col("close").last(),
            pl.col("pe_ratio").mean(),
            pl.col("pb_ratio").mean(),
            pl.col("mkt_cap").last(),
            pl.col("rev_growth_yoy").mean()
        ]).sort("month", descending=True).head(24)

        table = Table(title="HISTORIQUE DE VALORISATION (Mensuel)", box=ROUNDED, header_style="bold yellow", expand=True)
        table.add_column("Mois", style="dim")
        table.add_column("Prix Clôture", justify="right")
        table.add_column("PER", justify="right")
        table.add_column("P/B", justify="right")
        table.add_column("Market Cap", justify="right")
        
        for row in df_val.to_dicts():
            table.add_row(
                str(row["month"]),
                f"${row['close']:.2f}",
                f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
                f"{row['pb_ratio']:.2f}" if row['pb_ratio'] else "-",
                format_val(row['mkt_cap'])
            )
        return table

    # --- AFFICHAGE FINAL ---
    console.print(get_hist_table(is_annual=True))
    console.print(get_hist_table(is_annual=False))
    console.print(get_valuation_table())
    
    rprint(f"\n[dim italic]Source: SEC EDGAR | Data Point-In-Time | Last Analysis: {datetime.now().strftime('%H:%M:%S')}[/dim italic]")


def cmd_screen(args: argparse.Namespace):
    """Screener d'actions basé sur des critères temporels et fondamentaux."""
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            df = df.filter(pl.col("p_date") == target_date)
        except ValueError:
            rprint("[bold red]❌ Format de date invalide. Utilisez YYYY-MM-DD.[/bold red]")
            sys.exit(1)
    else:
        latest_date = df.select(pl.col("p_date").max()).collect()[0, 0]
        df = df.filter(pl.col("p_date") == latest_date)

    if args.pe_max: df = df.filter(pl.col("pe_ratio") < args.pe_max)
    if args.roe_min: df = df.filter(pl.col("roe") > args.roe_min)
    if args.sector: df = df.filter(pl.col("sector").str.to_lowercase().str.contains(args.sector.lower()))

    # Filtrage sécurisé via SQL
    if args.sql:
        ctx = pl.SQLContext()
        ctx.register("data", df)
        df = ctx.execute(f"SELECT * FROM data WHERE {args.sql}").lazy()

    try:
        final = df.collect()
    except Exception as e:
        rprint(f"[bold red]❌ Erreur lors de l'exécution : {e}[/bold red]")
        sys.exit(1)

    if args.silent:
        print(final.to_pandas().to_json(orient="records", default_handler=str))
        return

    if final.is_empty():
        rprint("[bold yellow]⚠️ Aucun résultat.[/bold yellow]")
        return

    table = Table(title=f"Screener Results", border_style="green")
    table.add_column("Ticker", style="bold magenta")
    table.add_column("Secteur")
    table.add_column("Prix")
    table.add_column("P/E")
    table.add_column("ROE %")
    table.add_column("Growth %")
    
    for row in final.head(args.limit).to_dicts():
        table.add_row(
            row.get('ticker', '-').upper(),
            str(row.get('sector', '-')),
            f"{row.get('close', 0):.2f}$" if row.get('close') is not None else "-",
            f"{row.get('pe_ratio'):.1f}" if row.get('pe_ratio') is not None else "-",
            f"{row.get('roe')*100:.1f}%" if row.get('roe') is not None else "-",
            f"{row.get('rev_growth_yoy')*100:.1f}%" if row.get('rev_growth_yoy') is not None else "-"
        )
    console.print(table)


def cmd_universe(args: argparse.Namespace):
    """Affiche toutes les entreprises disponibles dans la base de données."""
    try:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        latest_date = df.select(pl.col("p_date").max()).collect()[0, 0]
        
        universe = df.filter(pl.col("p_date") == latest_date).select([
            "ticker", "cik", "sector", "mkt_cap"
        ]).drop_nulls(subset=["ticker"]).sort("ticker").collect()
        
    except Exception as e:
        rprint(f"[bold red]❌ Erreur : {e}[/bold red]")
        return

    table = Table(title=f"UNIVERS DES ENTREPRISES ({latest_date})", border_style="green", box=ROUNDED)
    table.add_column("Ticker", style="bold magenta")
    table.add_column("Secteur")
    table.add_column("Market Cap", justify="right")
    
    for row in universe.to_dicts():
        table.add_row(
            row["ticker"].upper(),
            str(row["sector"]),
            format_val(row["mkt_cap"])
        )
    console.print(table)
    rprint(f"\n[bold green]Total : {len(universe)} entreprises répertoriées.[/bold green]")


def cmd_export(args: argparse.Namespace):
    """Exporte l'historique d'un ticker en CSV."""
    ticker = args.ticker.lower()
    output = args.output or f"{ticker}_history.csv"
    
    with console.status(f"[bold green]Exportation de {ticker.upper()}...[/bold green]"):
        try:
            df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).collect()
            if df.is_empty():
                rprint(f"[bold red]❌ Ticker {ticker.upper()} non trouvé.[/bold red]")
                return
            
            df.write_csv(output)
            rprint(f"[bold green]✅ Données exportées avec succès vers {output}[/bold green]")
        except Exception as e:
            rprint(f"[bold red]❌ Erreur d'exportation : {e}[/bold red]")


def main():
    parser = argparse.ArgumentParser(description="SMID-SEC RESEARCH TERMINAL")
    parser.add_argument("--silent", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="État du moteur")
    
    term_p = subparsers.add_parser("terminal", help="Analyse complète d'une entreprise")
    term_p.add_argument("ticker", help="Symbole (ex: AAPL)")
    
    subparsers.add_parser("universe", help="Liste toutes les entreprises")

    export_p = subparsers.add_parser("export", help="Export CSV de l'historique")
    export_p.add_argument("ticker", help="Symbole")
    export_p.add_argument("--output", help="Nom du fichier de sortie")
    
    screen_p = subparsers.add_parser("screen", help="Screener")
    screen_p.add_argument("--pe-max", type=float)
    screen_p.add_argument("--roe-min", type=float)
    screen_p.add_argument("--sql")
    screen_p.add_argument("--date")
    screen_p.add_argument("--limit", type=int, default=20)

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command:
        print_banner(args.silent)
        if not check_paths(): sys.exit(1)
        
        if args.command == "status": cmd_status(args)
        elif args.command == "terminal": cmd_terminal(args)
        elif args.command == "screen": cmd_screen(args)
        elif args.command == "universe": cmd_universe(args)
        elif args.command == "export": cmd_export(args)
        
if __name__ == "__main__":
    main()
