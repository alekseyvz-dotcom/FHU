import pandas as pd
from datetime import datetime
from typing import Dict, Any

class IncidentManager:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.mode = cfg["storage"]["mode"]
        self.mapping = cfg["mapping"]

    def load_incidents(self) -> pd.DataFrame:
        if self.mode == "excel":
            path = self.cfg["storage"]["excel_path"]
            sheet = self.mapping["incidents_sheet"]
            df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
            return self._normalize(df)
        elif self.mode == "csv":
            # пример: data/incidents.csv
            df = pd.read_csv(self.cfg["storage"]["csv_path"])
            return self._normalize(df)
        elif self.mode == "yandex":
            # Заглушка: подключим после получения доступа/требований к API
            raise NotImplementedError("Yandex Tables integration pending")
        else:
            raise ValueError(f"Unknown storage mode: {self.mode}")

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = self.mapping["columns"]
        rename_map = {
            cols["date"]: "date",
            cols["time"]: "time",
            cols["duty"]: "duty",
            cols["type"]: "type",
            cols["description"]: "description",
        }
        df = df.rename(columns=rename_map)
        # Приведение типов (можно уточнить под ваш файл)
        if "date" in df:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        if "time" in df:
            df["time"] = pd.to_datetime(df["time"], errors="coerce").dt.time
        return df
