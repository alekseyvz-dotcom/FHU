# report_generator.py
from datetime import date
import pandas as pd

class ReportGenerator:
    def __init__(self, cfg):
        self.cfg = cfg

    def build_daily_report(self, df: pd.DataFrame) -> str:
        today = date.today()
        title = f"Суточный отчёт за {today.strftime('%d.%m.%Y')}"
        if df is None or df.empty:
            return f"{title}\nИнцидентов не зарегистрировано."

        if "date" in df.columns:
            day_df = df[df["date"] == today]
        else:
            day_df = df

        lines = [title]
        if day_df.empty:
            lines.append("Инцидентов не зарегистрировано.")
        else:
            for _, row in day_df.iterrows():
                t = row.get("time")
                t_str = t.strftime("%H:%M") if pd.notna(t) and t else "-"
                duty = row.get("duty","")
                loc = row.get("location","")
                addr = row.get("address","")
                status = row.get("status","")
                extra = f" [{status}]" if status else ""
                lines.append(f"- {t_str} | {row.get('type','?')} | {loc} / {addr} | {duty}{extra} | {row.get('description','')}")
        return "\n".join(lines)
