import argparse
import sys
from pathlib import Path
import yaml
from incident_manager import IncidentManager
from report_generator import ReportGenerator
from telegram_bot import TelegramClient

def load_config(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def cmd_daily_report(cfg):
    im = IncidentManager(cfg)
    rg = ReportGenerator(cfg)
    tg = TelegramClient(cfg["telegram"]["token"], cfg["telegram"]["chat_id"])

    df = im.load_incidents()
    msg = rg.build_daily_report(df)
    tg.send_message(msg)
    print("Daily report sent.")

def cmd_incident(cfg, description, incident_type=None):
    im = IncidentManager(cfg)
    tg = TelegramClient(cfg["telegram"]["token"], cfg["telegram"]["chat_id"])
    # Здесь можно дополнить записью инцидента в таблицу (после уточнения схемы)
    msg = f"ИНЦИДЕНТ: {incident_type or 'Без типа'}\n{description}"
    tg.send_message(msg)
    print("Incident alert sent.")

def main():
    parser = argparse.ArgumentParser(prog="incident-reporter")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("daily-report")

    p_inc = sub.add_parser("incident")
    p_inc.add_argument("--type", dest="incident_type", default=None)
    p_inc.add_argument("description")

    args = parser.parse_args()
    cfg = load_config(Path(args.config))

    if args.command == "daily-report":
        cmd_daily_report(cfg)
    elif args.command == "incident":
        cmd_incident(cfg, args.description, args.incident_type)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
