from datetime import date
import pandas as pd

class ReportGenerator:
    def __init__(self, cfg):
        self.cfg = cfg

    def build_daily_report(self, df: pd.DataFrame) -> str:
        today = date.today()
        if "date" in df.columns:
            day_df = df[df["date"] == today]
        else:
            day_df = df

        lines = [f"Суточный отчёт за {today.strftime('%d.%m.%Y')}"]
        if day_df.empty:
            lines.append("Инцидентов не зарегистрировано.")
        else:
            for i, row in day_df.iterrows():
                t = row.get("time")
                t_str = t.strftime("%H:%M") if t else "-"
                lines.append(f"- {t_str} | {row.get('type','?')} | {row.get('description','')}")
        return "\n".join(lines)
