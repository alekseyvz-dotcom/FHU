# app.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
from typing import Optional
from config import load_config
from storage import IncidentStorage, DEFAULT_STATUS, CLOSED_STATUS
from report_generator import ReportGenerator
from telegram_client import TelegramClient

APP_TITLE = "Incident Reporter"

class HomeFrame(ttk.Frame):
    def __init__(self, master, on_make_report):
        super().__init__(master, padding=12)
        ttk.Label(self, text="Система докладов дежурных", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0,8))
        ttk.Label(self, text="Меню:\n- Инциденты → Создать инцидент\n- Инциденты → Реестр инцидентов\n- Доклад → Сформировать доклад\n- Справочники → Локации и адреса", justify="left").pack(anchor="w")
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=12)
        ttk.Button(self, text="Сформировать доклад за сегодня", command=on_make_report).pack(anchor="w")

class CreateIncidentDialog(tk.Toplevel):
    def __init__(self, master, cfg, storage: IncidentStorage, telegram: TelegramClient, on_saved=None):
        super().__init__(master)
        self.title("Создать инцидент")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)

        self.cfg = cfg
        self.storage = storage
        self.telegram = telegram
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        self.var_date = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        self.var_time = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        self.var_duty = tk.StringVar(value=cfg.get("ui", {}).get("default_duty", ""))
        self.var_type = tk.StringVar()
        self.var_desc = tk.StringVar()

        self.var_location = tk.StringVar()
        self.var_address = tk.StringVar()

        row = 0
        ttk.Label(frm, text="Дата:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.var_date, width=15).grid(row=row, column=1, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(frm, text="Время:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.var_time, width=15).grid(row=row, column=1, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(frm, text="Дежурный:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.var_duty, width=30).grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        ttk.Label(frm, text="Локация:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.cb_location = ttk.Combobox(frm, textvariable=self.var_location, values=self.storage.get_locations(), state="readonly", width=27)
        self.cb_location.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        self.cb_location.bind("<<ComboboxSelected>>", self._on_location_change)
        ttk.Button(frm, text="Справочник…", command=self._open_directory).grid(row=row, column=2, sticky="w", padx=5, pady=5)

        row += 1
        ttk.Label(frm, text="Адрес:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.cb_address = ttk.Combobox(frm, textvariable=self.var_address, values=[], state="readonly", width=27)
        self.cb_address.grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        ttk.Label(frm, text="Тип:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        ttk.Combobox(frm, textvariable=self.var_type, values=[
            "Сбой сервиса", "Инцидент безопасности", "Оповещение", "Другое"
        ], width=27).grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        ttk.Label(frm, text="Описание:").grid(row=row, column=0, sticky="ne", padx=5, pady=5)
        self.txt_desc = tk.Text(frm, width=60, height=6)
        self.txt_desc.grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        self.var_send_tg = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Сразу отправить в Telegram", variable=self.var_send_tg).grid(row=row, column=1, sticky="w", padx=5, pady=(5,10))

        row += 1
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="e")
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btns, text="Сохранить", command=self.on_save).pack(side="right", padx=5)

        # Предзаполнение адресов для первой локации (если есть)
        locs = self.storage.get_locations()
        if locs:
            self.var_location.set(locs[0])
            self._reload_addresses()

    def _on_location_change(self, *_):
        self._reload_addresses()

    def _reload_addresses(self):
        loc = self.var_location.get()
        addrs = self.storage.get_addresses(loc)
        self.cb_address["values"] = addrs
        self.var_address.set(addrs[0] if addrs else "")

    def _open_directory(self):
        LocationsManager(self, self.storage, on_close=self._after_dir_change)

    def _after_dir_change(self):
        # после изменения справочника — обновим выпадающие списки
        locs = self.storage.get_locations()
        self.cb_location["values"] = locs
        if self.var_location.get() not in locs:
            self.var_location.set(locs[0] if locs else "")
        self._reload_addresses()

    def on_save(self):
        self.var_desc.set(self.txt_desc.get("1.0", "end").strip())

        try:
            d = datetime.strptime(self.var_date.get(), "%d.%m.%Y").date()
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты. Используйте ДД.ММ.ГГГГ.")
            return
        try:
            t = datetime.strptime(self.var_time.get(), "%H:%M").time()
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат времени. Используйте ЧЧ:ММ.")
            return

        if not self.var_location.get():
            messagebox.showerror("Ошибка", "Выберите локацию.")
            return
        if not self.var_address.get():
            messagebox.showerror("Ошибка", "Выберите адрес.")
            return

        rec = {
            "id": None,
            "date": d,
            "time": t,
            "location": self.var_location.get(),
            "address": self.var_address.get(),
            "duty": self.var_duty.get().strip(),
            "type": self.var_type.get().strip() or "Без типа",
            "description": self.var_desc.get().strip(),
            "status": DEFAULT_STATUS,
            "resolved_at": None,
            "comment": "",
        }
        if not rec["description"]:
            messagebox.showerror("Ошибка", "Описание не может быть пустым.")
            return

        try:
            self.storage.append_incident(rec)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить инцидент:\n{e}")
            return

        if self.var_send_tg.get():
            try:
                text = (
                    "ИНЦИДЕНТ\n"
                    f"Дата: {d.strftime('%d.%m.%Y')}\n"
                    f"Время: {t.strftime('%H:%M')}\n"
                    f"Локация: {rec['location']}\n"
                    f"Адрес: {rec['address']}\n"
                    f"Дежурный: {rec['duty']}\n"
                    f"Тип: {rec['type']}\n"
                    f"Описание: {rec['description']}"
                )
                self.telegram.send_message(text)
            except Exception as e:
                messagebox.showwarning("Telegram", f"Инцидент сохранён, но не удалось отправить в Telegram:\n{e}")

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo("Готово", "Инцидент сохранён.")
        self.destroy()

class RegistryWindow(tk.Toplevel):
    def __init__(self, master, storage: IncidentStorage):
        super().__init__(master)
        self.title("Реестр инцидентов")
        self.geometry("1100x500")
        self.storage = storage

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        toolbar = ttk.Frame(frm)
        toolbar.pack(fill="x")
        self.var_filter_date = tk.StringVar(value="")
        ttk.Label(toolbar, text="Дата (ДД.ММ.ГГГГ):").pack(side="left", padx=(0,6))
        ttk.Entry(toolbar, textvariable=self.var_filter_date, width=12).pack(side="left")
        ttk.Button(toolbar, text="Применить", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Сброс", command=self.reset_filter).pack(side="left", padx=6)

        columns = ("id","date","time","location","address","duty","type","description","status","resolved_at")
        self.tree = ttk.Treeview(frm, columns=columns, show="headings", height=16)
        self.tree.pack(fill="both", expand=True, pady=(6,0))
        headers = {
            "id":"ID","date":"Дата","time":"Время","location":"Локация","address":"Адрес",
            "duty":"Дежурный","type":"Тип","description":"Описание","status":"Статус","resolved_at":"Исправлено"
        }
        widths = {"id":60,"date":90,"time":80,"location":140,"address":200,"duty":150,"type":160,"description":400,"status":100,"resolved_at":120}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="w")

        self.tree.bind("<Double-1>", self.on_double_click)

        self.refresh()

    def reset_filter(self):
        self.var_filter_date.set("")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            df = self.storage.load_incidents()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить реестр:\n{e}")
            return

        f = self.var_filter_date.get().strip()
        if f:
            try:
                target = datetime.strptime(f, "%d.%m.%Y").date()
                df = df[df["date"] == target]
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты фильтра.")
                return

        if df is not None and not df.empty:
            df = df.sort_values(by=["date","time","id"], ascending=[False, False, False])
            for _, r in df.iterrows():
                d = r.get("date")
                t = r.get("time")
                ra = r.get("resolved_at")
                self.tree.insert("", "end", values=(
                    int(r.get("id")) if not pd.isna(r.get("id")) else "",
                    d.strftime("%d.%m.%Y") if pd.notna(d) and d else "",
                    t.strftime("%H:%M") if pd.notna(t) and t else "",
                    r.get("location",""),
                    r.get("address",""),
                    r.get("duty",""),
                    r.get("type",""),
                    r.get("description",""),
                    r.get("status",""),
                    ra.strftime("%d.%m.%Y %H:%M") if pd.notna(ra) and ra else "",
                ))

    def on_double_click(self, event):
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item, "values")
        if not values:
            return
        try:
            incident_id = int(values[0])
        except Exception:
            return
        IncidentDetailsDialog(self, self.storage, incident_id, on_saved=self.refresh)

class IncidentDetailsDialog(tk.Toplevel):
    def __init__(self, master, storage: IncidentStorage, incident_id: int, on_saved=None):
        super().__init__(master)
        self.title(f"Инцидент #{incident_id}")
        self.resizable(False, False)
        self.grab_set()
        self.storage = storage
        self.incident_id = incident_id
        self.on_saved = on_saved

        # Загружаем запись
        df = self.storage.load_incidents()
        row = df[df["id"] == incident_id]
        if row.empty:
            messagebox.showerror("Ошибка", f"Инцидент id={incident_id} не найден.")
            self.destroy()
            return
        self.row = row.iloc[0]

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        # Поля (некоторые только для чтения)
        rowi = 0
        def add_row(label, value):
            nonlocal rowi
            ttk.Label(frm, text=label + ":").grid(row=rowi, column=0, sticky="e", padx=5, pady=4)
            ttk.Label(frm, text=value).grid(row=rowi, column=1, sticky="w", padx=5, pady=4)
            rowi += 1

        add_row("ID", str(incident_id))
        add_row("Дата", self._fmt_date(self.row.get("date")))
        add_row("Время", self._fmt_time(self.row.get("time")))
        add_row("Локация", self.row.get("location",""))
        add_row("Адрес", self.row.get("address",""))
        add_row("Дежурный", self.row.get("duty",""))
        add_row("Тип", self.row.get("type",""))

        ttk.Label(frm, text="Описание:").grid(row=rowi, column=0, sticky="ne", padx=5, pady=4)
        txt_desc = tk.Text(frm, width=60, height=4)
        txt_desc.insert("1.0", str(self.row.get("description","")))
        txt_desc.configure(state="disabled")
        txt_desc.grid(row=rowi, column=1, sticky="w", padx=5, pady=4)
        rowi += 1

        ttk.Label(frm, text="Статус:").grid(row=rowi, column=0, sticky="e", padx=5, pady=4)
        self.var_status = tk.StringVar(value=self.row.get("status", DEFAULT_STATUS))
        cb_status = ttk.Combobox(frm, textvariable=self.var_status, values=[DEFAULT_STATUS, CLOSED_STATUS], state="readonly", width=20)
        cb_status.grid(row=rowi, column=1, sticky="w", padx=5, pady=4)
        cb_status.bind("<<ComboboxSelected>>", self._on_status_change)
        rowi += 1

        ttk.Label(frm, text="Время исправления:").grid(row=rowi, column=0, sticky="e", padx=5, pady=4)
        self.var_resolved_date = tk.StringVar(value=self._fmt_date(self.row.get("resolved_at")))
        self.var_resolved_time = tk.StringVar(value=self._fmt_time(self.row.get("resolved_at")))
        self.ent_resolved_date = ttk.Entry(frm, textvariable=self.var_resolved_date, width=12)
        self.ent_resolved_time = ttk.Entry(frm, textvariable=self.var_resolved_time, width=8)
        cont = ttk.Frame(frm)
        cont.grid(row=rowi, column=1, sticky="w")
        self.ent_resolved_date.pack(in_=cont, side="left", padx=(0,6))
        self.ent_resolved_time.pack(in_=cont, side="left")
        rowi += 1

        ttk.Label(frm, text="Комментарий:").grid(row=rowi, column=0, sticky="ne", padx=5, pady=4)
        self.txt_comment = tk.Text(frm, width=60, height=4)
        self.txt_comment.insert("1.0", str(self.row.get("comment","")))
        self.txt_comment.grid(row=rowi, column=1, sticky="w", padx=5, pady=4)
        rowi += 1

        btns = ttk.Frame(frm)
        btns.grid(row=rowi, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btns, text="Сохранить", command=self._save).pack(side="right", padx=5)

        # Применить состояние контролов по статусу
        self._apply_status_controls()

    def _fmt_date(self, d) -> str:
        try:
            if d and hasattr(d, "strftime"):
                return d.strftime("%d.%m.%Y")
        except Exception:
            pass
        return ""

    def _fmt_time(self, t) -> str:
        try:
            if t and hasattr(t, "strftime"):
                return t.strftime("%H:%M")
        except Exception:
            pass
        return ""

    def _on_status_change(self, *_):
        self._apply_status_controls()

    def _apply_status_controls(self):
        is_closed = self.var_status.get() == CLOSED_STATUS
        state = "normal" if is_closed else "disabled"
        self.ent_resolved_date.configure(state=state)
        self.ent_resolved_time.configure(state=state)
        if is_closed and not self.var_resolved_date.get():
            now = datetime.now()
            self.var_resolved_date.set(now.strftime("%d.%m.%Y"))
            self.var_resolved_time.set(now.strftime("%H:%M"))
        if not is_closed:
            self.var_resolved_date.set("")
            self.var_resolved_time.set("")

    def _save(self):
        status = self.var_status.get()
        comment = self.txt_comment.get("1.0", "end").strip()

        resolved_at = None
        if status == CLOSED_STATUS:
            d = self.var_resolved_date.get().strip()
            t = self.var_resolved_time.get().strip()
            if not d or not t:
                messagebox.showerror("Ошибка", "Укажите дату и время исправления.")
                return
            try:
                resolved_at = datetime.strptime(f"{d} {t}", "%d.%m.%Y %H:%M")
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат времени исправления. Используйте ДД.ММ.ГГГГ и ЧЧ:ММ.")
                return

        fields = {"status": status, "comment": comment, "resolved_at": resolved_at}
        try:
            self.storage.update_incident(self.incident_id, fields)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить изменения:\n{e}")
            return
        if self.on_saved:
            self.on_saved()
        self.destroy()

class ReportDialog(tk.Toplevel):
    def __init__(self, master, report_text: str, on_send_telegram):
        super().__init__(master)
        self.title("Суточный доклад")
        self.geometry("700x500")
        self.grab_set()

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        txt = tk.Text(frm, wrap="word")
        txt.insert("1.0", report_text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8,0))
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Отправить в Telegram", command=lambda: (on_send_telegram(), self.destroy())).pack(side="right", padx=6)

class LocationsManager(tk.Toplevel):
    def __init__(self, master, storage: IncidentStorage, on_close=None):
        super().__init__(master)
        self.title("Справочник: Локации и адреса")
        self.geometry("700x400")
        self.grab_set()
        self.storage = storage
        self.on_close = on_close

        self.df = self.storage.load_locations()

        main = ttk.Frame(self, padding=8)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True, padx=(0,6))
        right.pack(side="left", fill="both", expand=True, padx=(6,0))

        ttk.Label(left, text="Локации:").pack(anchor="w")
        self.lb_locations = tk.Listbox(left, height=15)
        self.lb_locations.pack(fill="both", expand=True)
        self.lb_locations.bind("<<ListboxSelect>>", self._on_loc_select)

        btns_loc = ttk.Frame(left)
        btns_loc.pack(fill="x", pady=(6,0))
        ttk.Button(btns_loc, text="Добавить", command=self._add_location).pack(side="left", padx=3)
        ttk.Button(btns_loc, text="Переименовать", command=self._rename_location).pack(side="left", padx=3)
        ttk.Button(btns_loc, text="Удалить", command=self._delete_location).pack(side="left", padx=3)

        ttk.Label(right, text="Адреса:").pack(anchor="w")
        self.lb_addresses = tk.Listbox(right, height=15)
        self.lb_addresses.pack(fill="both", expand=True)

        btns_addr = ttk.Frame(right)
        btns_addr.pack(fill="x", pady=(6,0))
        ttk.Button(btns_addr, text="Добавить", command=self._add_address).pack(side="left", padx=3)
        ttk.Button(btns_addr, text="Изменить", command=self._edit_address).pack(side="left", padx=3)
        ttk.Button(btns_addr, text="Удалить", command=self._delete_address).pack(side="left", padx=3)

        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8,0))
        ttk.Button(bottom, text="Закрыть", command=self._close).pack(side="right", padx=5)
        ttk.Button(bottom, text="Сохранить", command=self._save).pack(side="right", padx=5)

        self._reload_locations()

    def _reload_locations(self):
        self.lb_locations.delete(0, "end")
        locs = sorted(self.df["location"].unique().tolist())
        for l in locs:
            self.lb_locations.insert("end", l)
        if locs:
            self.lb_locations.selection_set(0)
            self._reload_addresses(locs[0])
        else:
            self.lb_addresses.delete(0, "end")

    def _current_location(self) -> Optional[str]:
        sel = self.lb_locations.curselection()
        if not sel:
            return None
        return self.lb_locations.get(sel[0])

    def _reload_addresses(self, location: Optional[str] = None):
        if location is None:
            location = self._current_location()
        self.lb_addresses.delete(0, "end")
        if not location:
            return
        addrs = self.df[self.df["location"] == location]["address"].tolist()
        for a in addrs:
            self.lb_addresses.insert("end", a)

    def _on_loc_select(self, *_):
        self._reload_addresses()

    def _add_location(self):
        name = simpledialog.askstring("Локация", "Название локации:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        # если локация не существует — добавим пустую строку для неё (без адреса пока)
        if name not in self.df["location"].unique():
            self.df = pd.concat([self.df, pd.DataFrame([{"location": name, "address": ""}])], ignore_index=True)
        self._reload_locations()
        # выставим курсор на новую
        idx = list(self.lb_locations.get(0, "end")).index(name)
        self.lb_locations.selection_clear(0, "end")
        self.lb_locations.selection_set(idx)
        self._reload_addresses(name)

    def _rename_location(self):
        cur = self._current_location()
        if not cur:
            return
        name = simpledialog.askstring("Переименование", "Новое название локации:", initialvalue=cur, parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self.df.loc[self.df["location"] == cur, "location"] = name
        self._reload_locations()

    def _delete_location(self):
        cur = self._current_location()
        if not cur:
            return
        if not messagebox.askyesno("Подтвердите", f"Удалить локацию '{cur}' и все её адреса?"):
            return
        self.df = self.df[self.df["location"] != cur]
        self._reload_locations()

    def _add_address(self):
        loc = self._current_location()
        if not loc:
            messagebox.showwarning("Локации", "Сначала добавьте/выберите локацию.")
            return
        addr = simpledialog.askstring("Адрес", "Введите адрес:", parent=self)
        if not addr:
            return
        addr = addr.strip()
        if not addr:
            return
        self.df = pd.concat([self.df, pd.DataFrame([{"location": loc, "address": addr}])], ignore_index=True)
        self._reload_addresses(loc)

    def _edit_address(self):
        loc = self._current_location()
        if not loc:
            return
        sel = self.lb_addresses.curselection()
        if not sel:
            return
        old = self.lb_addresses.get(sel[0])
        new = simpledialog.askstring("Адрес", "Новый адрес:", initialvalue=old, parent=self)
        if not new:
            return
        new = new.strip()
        if not new:
            return
        idx = self.df[(self.df["location"] == loc) & (self.df["address"] == old)].index
        self.df.loc[idx, "address"] = new
        self._reload_addresses(loc)

    def _delete_address(self):
        loc = self._current_location()
        if not loc:
            return
        sel = self.lb_addresses.curselection()
        if not sel:
            return
        addr = self.lb_addresses.get(sel[0])
        self.df = self.df[~((self.df["location"] == loc) & (self.df["address"] == addr))]
        # Если у локации не осталось строк — добавим пустую (чтоб локация не пропала сразу)
        if self.df[self.df["location"] == loc].empty:
            self.df = pd.concat([self.df, pd.DataFrame([{"location": loc, "address": ""}])], ignore_index=True)
        self._reload_addresses(loc)

    def _save(self):
        try:
            self.storage.save_locations(self.df)
            messagebox.showinfo("Готово", "Справочник сохранён.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить справочник:\n{e}")

    def _close(self):
        # При закрытии просто уведомим родителя, что справочник мог измениться
        if self.on_close:
            try:
                self.storage.save_locations(self.df)
            except Exception:
                pass
            self.on_close()
        self.destroy()

class ReportDialog(tk.Toplevel):
    # (без изменений от предыдущей версии)
    def __init__(self, master, report_text: str, on_send_telegram):
        super().__init__(master)
        self.title("Суточный доклад")
        self.geometry("700x500")
        self.grab_set()

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        txt = tk.Text(frm, wrap="word")
        txt.insert("1.0", report_text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8,0))
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Отправить в Telegram", command=lambda: (on_send_telegram(), self.destroy())).pack(side="right", padx=6)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1060x640")

        self.cfg = load_config("config.yaml")
        self.storage = IncidentStorage(self.cfg["storage"]["excel_path"])
        self.reporter = ReportGenerator(self.cfg)
        self.telegram = TelegramClient(self.cfg["telegram"]["token"], self.cfg["telegram"]["chat_id"])

        self.home = HomeFrame(self, self.on_make_report)
        self.home.pack(fill="both", expand=True)

        self.create_menu()

    def create_menu(self):
        m = tk.Menu(self)
        # Главная
        menu_home = tk.Menu(m, tearoff=0)
        menu_home.add_command(label="Панель", command=self.show_home)
        menu_home.add_separator()
        menu_home.add_command(label="Проверить Telegram", command=self.check_telegram)
        menu_home.add_command(label="О программе", command=lambda: messagebox.showinfo("О программе", APP_TITLE))
        m.add_cascade(label="Главная", menu=menu_home)

        # Инциденты
        menu_inc = tk.Menu(m, tearoff=0)
        menu_inc.add_command(label="Создать инцидент", command=self.open_create_incident)
        menu_inc.add_command(label="Реестр инцидентов", command=self.open_registry)
        m.add_cascade(label="Инциденты", menu=menu_inc)

        # Доклад
        menu_rep = tk.Menu(m, tearoff=0)
        menu_rep.add_command(label="Сформировать доклад", command=self.on_make_report)
        m.add_cascade(label="Доклад", menu=menu_rep)

        # Справочники
        menu_dir = tk.Menu(m, tearoff=0)
        menu_dir.add_command(label="Локации и адреса", command=self.open_locations_manager)
        m.add_cascade(label="Справочники", menu=menu_dir)

        self.config(menu=m)

    def show_home(self):
        for w in self.winfo_children():
            if isinstance(w, ttk.Frame) and w is not self.home:
                w.pack_forget()
        self.home.pack(fill="both", expand=True)

    def check_telegram(self):
        try:
            self.telegram.send_message("Проверка соединения: приложение активно.")
            messagebox.showinfo("Telegram", "Сообщение отправлено.")
        except Exception as e:
            messagebox.showerror("Telegram", f"Не удалось отправить сообщение:\n{e}")

    def open_create_incident(self):
        CreateIncidentDialog(self, self.cfg, self.storage, self.telegram, on_saved=None)

    def open_registry(self):
        RegistryWindow(self, self.storage)

    def open_locations_manager(self):
        LocationsManager(self, self.storage)

    def on_make_report(self):
        try:
            df = self.storage.load_incidents()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные для доклада:\n{e}")
            return
        text = self.reporter.build_daily_report(df)
        def send():
            try:
                self.telegram.send_message(text)
                messagebox.showinfo("Готово", "Доклад отправлен в Telegram.")
            except Exception as e:
                messagebox.showerror("Telegram", f"Не удалось отправить доклад:\n{e}")
        ReportDialog(self, text, send)

if __name__ == "__main__":
    App().mainloop()
