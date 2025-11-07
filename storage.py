# storage.py
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from datetime import datetime

INCIDENT_SHEET = "Incidents"
LOCATIONS_SHEET = "Locations"

INCIDENT_COLUMNS = [
    "id", "date", "time",
    "location", "address",
    "duty", "type", "description",
    "status", "resolved_at", "comment",
]

# Значения по умолчанию
DEFAULT_STATUS = "Открыт"
CLOSED_STATUS = "Закрыт"

class IncidentStorage:
    def __init__(self, excel_path: str):
        self.path = Path(excel_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._create_empty()

    def _create_empty(self):
        # Пустые листы
        inc_df = pd.DataFrame(columns=INCIDENT_COLUMNS)
        loc_df = pd.DataFrame(columns=["location", "address"])
        with pd.ExcelWriter(self.path, engine="openpyxl") as w:
            inc_df.to_excel(w, sheet_name=INCIDENT_SHEET, index=False)
            loc_df.to_excel(w, sheet_name=LOCATIONS_SHEET, index=False)

    # Универсальная запись одного листа без перезаписи других
    def _write_sheet(self, sheet_name: str, df: pd.DataFrame):
        if not self.path.exists():
            # если файла нет — создаём и пишем только этот лист
            with pd.ExcelWriter(self.path, engine="openpyxl") as w:
                df.to_excel(w, sheet_name=sheet_name, index=False)
            return
        # если файл есть — заменяем только нужный лист
        with pd.ExcelWriter(self.path, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
            df.to_excel(w, sheet_name=sheet_name, index=False)

    # ---- Incidents ----
    def _ensure_incidents_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        # Добавить недостающие колонки
        for c in INCIDENT_COLUMNS:
            if c not in df.columns:
                df[c] = pd.NA

        # Типы
        if "id" in df.columns:
            # безопасно привести к Int64 (nullable)
            df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], errors="coerce").dt.time
        if "resolved_at" in df.columns:
            df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce")
        # Статус по умолчанию
        if "status" in df.columns:
            df["status"] = df["status"].fillna(DEFAULT_STATUS)

        # Переупорядочить колонки
        df = df[INCIDENT_COLUMNS]
        return df

    def load_incidents(self) -> pd.DataFrame:
        if not self.path.exists():
            self._create_empty()
        df = pd.read_excel(self.path, sheet_name=INCIDENT_SHEET, engine="openpyxl")
        return self._ensure_incidents_schema(df)

    def _next_id(self, df: pd.DataFrame) -> int:
        if df.empty or df["id"].isna().all():
            return 1
        return int(df["id"].max()) + 1

    def append_incident(self, record: Dict[str, Any]):
        df = self.load_incidents()
        if pd.isna(record.get("id")) or record.get("id") is None:
            record["id"] = self._next_id(df)
        # Значения по умолчанию
        record.setdefault("status", DEFAULT_STATUS)
        record.setdefault("resolved_at", pd.NaT)
        record.setdefault("comment", "")

        # Создаём DataFrame и записываем
        new_row = pd.DataFrame([record])
        df = pd.concat([df, new_row], ignore_index=True)
        # Приведение типов/схемы перед записью
        df = self._ensure_incidents_schema(df)
        self._write_sheet(INCIDENT_SHEET, df)

    def update_incident(self, incident_id: int, fields: Dict[str, Any]):
        df = self.load_incidents()
        if df.empty:
            raise ValueError("Реестр инцидентов пуст.")
        mask = df["id"] == incident_id
        if not mask.any():
            raise ValueError(f"Инцидент id={incident_id} не найден.")

        for k, v in fields.items():
            if k == "resolved_at":
                # допускаем None/пусто для очистки
                if v in (None, "", pd.NaT):
                    df.loc[mask, "resolved_at"] = pd.NaT
                else:
                    # поддержка строки "ДД.ММ.ГГГГ ЧЧ:ММ"
                    if isinstance(v, str):
                        try:
                            v_parsed = datetime.strptime(v, "%d.%m.%Y %H:%M")
                        except ValueError:
                            # альтернативный ISO
                            v_parsed = pd.to_datetime(v, errors="coerce")
                        df.loc[mask, "resolved_at"] = v_parsed
                    else:
                        df.loc[mask, "resolved_at"] = v
            elif k in ("date",):
                if isinstance(v, str) and v:
                    try:
                        df.loc[mask, "date"] = datetime.strptime(v, "%d.%m.%Y").date()
                    except ValueError:
                        df.loc[mask, "date"] = pd.to_datetime(v, errors="coerce").date()
                else:
                    df.loc[mask, "date"] = v
            elif k in ("time",):
                if isinstance(v, str) and v:
                    try:
                        df.loc[mask, "time"] = datetime.strptime(v, "%H:%M").time()
                    except ValueError:
                        df.loc[mask, "time"] = pd.to_datetime(v, errors="coerce").time()
                else:
                    df.loc[mask, "time"] = v
            else:
                df.loc[mask, k] = v

        df = self._ensure_incidents_schema(df)
        self._write_sheet(INCIDENT_SHEET, df)

    # ---- Locations ----
    def load_locations(self) -> pd.DataFrame:
        if not self.path.exists():
            self._create_empty()
        try:
            df = pd.read_excel(self.path, sheet_name=LOCATIONS_SHEET, engine="openpyxl")
        except ValueError:
            # если листа нет — создадим
            df = pd.DataFrame(columns=["location", "address"])
            self._write_sheet(LOCATIONS_SHEET, df)

        # Приведение типов/колонок
        for c in ["location", "address"]:
            if c not in df.columns:
                df[c] = ""
        df = df[["location", "address"]]
        df["location"] = df["location"].fillna("").astype(str)
        df["address"] = df["address"].fillna("").astype(str)
        return df

    def save_locations(self, df: pd.DataFrame):
        # Оставляем только нужные колонки
        if "location" not in df.columns or "address" not in df.columns:
            raise ValueError("Таблица локаций должна содержать колонки: location, address")
        clean = df[["location", "address"]].copy()
        # Удалим пустые строки
        clean = clean[(clean["location"].str.strip() != "") & (clean["address"].str.strip() != "")]
        self._write_sheet(LOCATIONS_SHEET, clean)

    def get_locations(self) -> List[str]:
        df = self.load_locations()
        locs = sorted(df["location"].dropna().unique().tolist())
        return locs

    def get_addresses(self, location: str) -> List[str]:
        df = self.load_locations()
        if not location:
            return []
        subset = df[df["location"] == location]
        addrs = sorted(subset["address"].dropna().unique().tolist())
        return addrs
