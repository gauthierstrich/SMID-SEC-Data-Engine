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
    [bold white]SMID-SEC Data Engine | Institutional Research Terminal v1.3[/bold white]
    """
    console.print(banner)

def cmd_status(args):
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

    table = Table(title="Statistiques du Moteur Alpha", border_style="cyan")
    table.add_column("Métrique", style="bold magenta")
    table.add_column("Valeur", style="bold white")
    table.add_row("Lignes totales", f"{stats[0, 'rows']:,}")
    table.add_row("Entreprises", f"{stats[0, 'tickers']:,}")
    table.add_row("Historique", f"{stats[0, 'start']} au {stats[0, 'end']}")
    
    # Affichage des colonnes disponibles
    schema = df.collect_schema().names()
    table.add_row("Colonnes dispos", f"{len(schema)} (voir docs/ALPHA_SPEC)")
    console.print(table)

def cmd_screen(args):
    target_date = args.date if args.date else "2026-04-02"
    df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("p_date") == target_date)
    
    # --- MOTEUR DE REQUÊTE DYNAMIQUE ---
    if args.query:
        try:
            # On utilise le moteur d'expression de Polars via eval sur une chaine d'expression
            # On parse la query pour transformer les noms de colonnes en expressions pl.col()
            # Pour la simplicité, on conseille à l'utilisateur d'utiliser la syntaxe standard.
            # Ici on va supporter une syntaxe simplifiée pour le CLI
            res = df.filter(eval(args.query))
        except Exception as e:
            rprint(f"[bold red]❌ Erreur de syntaxe dans la requête : {e}[/bold red]")
            return
    else:
        res = df
        if args.pe_max: res = res.filter(pl.col("pe_ratio") < args.pe_max)
        if args.roe_min: res = res.filter(pl.col("roe") > args.roe_min)

    final = res.collect()
    
    if args.silent:
        print(final.to_pandas().to_json(orient="records"))
        return

    if final.is_empty():
        rprint("[bold red]❌ Aucun résultat.[/bold red]")
    else:
        table = Table(title=f"Resultats du Screening ({target_date})", border_style="green")
        table.add_column("Ticker", style="bold magenta")
        table.add_column("Secteur")
        table.add_column("Prix")
        table.add_column("P/E")
        table.add_column("ROE %")
        table.add_column("Growth %")
        
        for row in final.sort("rev_growth_yoy", descending=True).head(20).to_dicts():
            table.add_row(
                row['ticker'].upper(), row['sector'],
                f"{row['close']:.2f}$",
                f"{row['pe_ratio']:.1f}" if row['pe_ratio'] else "-",
                f"{row['roe']*100:.1f}%" if row['roe'] else "-",
                f"{row['rev_growth_yoy']*100:.1f}%" if row['rev_growth_yoy'] else "-"
            )
        console.print(table)

def cmd_export(args):
    with console.status(f"[bold green]Extraction du dataset de recherche...") as status:
        df = pl.scan_parquet(ALPHA_MATRIX_PATH)
        
        # Filtres de base
        if args.start: df = df.filter(pl.col("p_date") >= datetime.strptime(args.start, "%Y-%m-%d").date())
        if args.end: df = df.filter(pl.col("p_date") <= datetime.strptime(args.end, "%Y-%m-%d").date())
        
        # Requête complexe lors de l'export (Permet de générer des univers sur mesure)
        if args.query:
            df = df.filter(eval(args.query))
            
        if args.cols:
            cols = ["ticker", "p_date"] + args.cols.split(",")
            df = df.select([c for c in cols if c in df.collect_schema().names()])
        
        final = df.collect()
        final.write_parquet(args.output, compression="zstd")
    
    if not args.silent:
        rprint(f"\n[bold green]✅ Exportation de {len(final):,} lignes terminée -> {args.output}[/bold green]")

def main():
    parser = argparse.ArgumentParser(
        description="SMID-SEC RESEARCH TERMINAL : L'outil ultime pour le backtesting et la recherche d'anomalies.",
        add_help=True
    )
    parser.add_argument("--silent", action="store_true", help="Désactive l'UI (Machine-to-Machine)")
    subparsers = parser.add_subparsers(dest="command")

    # Commandes
    subparsers.add_parser("status", help="Affiche les colonnes et statistiques")
    
    get_p = subparsers.add_parser("get", help="Historique d'un ticker")
    get_p.add_argument("ticker")
    get_p.add_argument("--limit", type=int, default=10)

    screen_p = subparsers.add_parser("screen", help="Screener dynamique")
    screen_p.add_argument("--date", help="Date YYYY-MM-DD")
    screen_p.add_argument("--query", help="Requête Polars (ex: '(pl.col(\"pe_ratio\") < 15) & (pl.col(\"roe\") > 0.2)')")
    screen_p.add_argument("--pe-max", type=float)
    screen_p.add_argument("--roe-min", type=float)
    screen_p.add_argument("--sector")

    export_p = subparsers.add_parser("export", help="Préparation de Backtest")
    export_p.add_argument("--output", required=True, help="Nom du fichier .parquet")
    export_p.add_argument("--start", help="Date début")
    export_p.add_argument("--end", help="Date fin")
    export_p.add_argument("--query", help="Filtre d'univers complexe")
    export_p.add_argument("--cols", help="Colonnes spécifiques (ex: close,pe_ratio,revenue)")

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command:
        print_banner(args.silent)
        if args.command == "status": cmd_status(args)
        elif args.command == "get":
            # On simule l'objet args pour cmd_get
            from types import SimpleNamespace
            ticker = args.ticker.lower()
            df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == ticker).tail(args.limit).collect()
            if df.is_empty(): rprint(f"[bold red]❌ Non trouvé.[/bold red]")
            else: rprint(df)
        elif args.command == "screen": cmd_screen(args)
        elif args.command == "export": cmd_export(args)

if __name__ == "__main__":
    main()
