# storage.py
import os
from pathlib import Path
from typing import Dict, Any
import pandas as pd

COLUMNS = ["date", "time", "duty", "type", "description"]

class IncidentStorage:
    def __init__(self, excel_path: str):
        self.path = Path(excel_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._create_empty()

    def _create_empty(self):
        df = pd.DataFrame(columns=COLUMNS)
        with pd.ExcelWriter(self.path, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Incidents", index=False)

    def load_incidents(self) -> pd.DataFrame:
        if not self.path.exists():
            self._create_empty()
        df = pd.read_excel(self.path, sheet_name="Incidents", engine="openpyxl")
        # Приведение типов
        if "date" in df:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        if "time" in df:
            df["time"] = pd.to_datetime(df["time"], errors="coerce").dt.time
        return df

    def append_incident(self, record: Dict[str, Any]):
        df = self.load_incidents()
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        with pd.ExcelWriter(self.path, engine="openpyxl", mode="w") as w:
            df.to_excel(w, sheet_name="Incidents", index=False)
