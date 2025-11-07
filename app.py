# app.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from config import load_config
from storage import IncidentStorage
from report_generator import ReportGenerator
from telegram_client import TelegramClient

APP_TITLE = "Incident Reporter"

class HomeFrame(ttk.Frame):
    def __init__(self, master, on_make_report):
        super().__init__(master, padding=12)
        ttk.Label(self, text="Система докладов дежурных", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0,8))
        ttk.Label(self, text="Выберите действие в меню:\n- Инциденты → Создать инцидент\n- Инциденты → Реестр инцидентов\n- Доклад → Сформировать доклад", justify="left").pack(anchor="w")
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=12)
        ttk.Button(self, text="Сформировать доклад за сегодня", command=on_make_report).pack(anchor="w")

class CreateIncidentDialog(tk.Toplevel):
    def __init__(self, master, cfg, storage: IncidentStorage, telegram: TelegramClient):
        super().__init__(master)
        self.title("Создать инцидент")
        self.resizable(False, False)
        self.grab_set()

        self.cfg = cfg
        self.storage = storage
        self.telegram = telegram

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        # Поля ввода
        self.var_date = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        self.var_time = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        self.var_duty = tk.StringVar(value=cfg.get("ui", {}).get("default_duty", ""))
        self.var_type = tk.StringVar()
        self.var_desc = tk.StringVar()

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
        ttk.Label(frm, text="Тип:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        ttk.Combobox(frm, textvariable=self.var_type, values=[
            "Сбой сервиса", "Инцидент безопасности", "Оповещение", "Другое"
        ], width=27).grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        ttk.Label(frm, text="Описание:").grid(row=row, column=0, sticky="ne", padx=5, pady=5)
        self.txt_desc = tk.Text(frm, width=50, height=6)
        self.txt_desc.grid(row=row, column=1, sticky="w", padx=5, pady=5, columnspan=2)

        row += 1
        self.var_send_tg = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Сразу отправить в Telegram", variable=self.var_send_tg).grid(row=row, column=1, sticky="w", padx=5, pady=(5,10))

        # Кнопки
        row += 1
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="e")
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btns, text="Сохранить", command=self.on_save).pack(side="right", padx=5)

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

        rec = {
            "date": d,
            "time": t,
            "duty": self.var_duty.get().strip(),
            "type": self.var_type.get().strip() or "Без типа",
            "description": self.var_desc.get().strip(),
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
                text = f"ИНЦИДЕНТ\nДата: {d.strftime('%d.%m.%Y')}\nВремя: {t.strftime('%H:%M')}\nДежурный: {rec['duty']}\nТип: {rec['type']}\nОписание: {rec['description']}"
                self.telegram.send_message(text)
            except Exception as e:
                messagebox.showwarning("Telegram", f"Инцидент сохранён, но не удалось отправить в Telegram:\n{e}")

        messagebox.showinfo("Готово", "Инцидент сохранён.")
        self.destroy()

class RegistryWindow(tk.Toplevel):
    def __init__(self, master, storage: IncidentStorage):
        super().__init__(master)
        self.title("Реестр инцидентов")
        self.geometry("900x400")
        self.storage = storage

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)

        toolbar = ttk.Frame(frm)
        toolbar.pack(fill="x")
        self.var_filter_date = tk.StringVar(value="")
        ttk.Label(toolbar, text="Фильтр по дате (ДД.ММ.ГГГГ):").pack(side="left", padx=(0,6))
        ttk.Entry(toolbar, textvariable=self.var_filter_date, width=12).pack(side="left")
        ttk.Button(toolbar, text="Применить", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Сброс", command=self.reset_filter).pack(side="left", padx=6)

        columns = ("date","time","duty","type","description")
        self.tree = ttk.Treeview(frm, columns=columns, show="headings", height=15)
        self.tree.pack(fill="both", expand=True, pady=(6,0))
        headers = {
            "date":"Дата","time":"Время","duty":"Дежурный","type":"Тип","description":"Описание"
        }
        widths = {"date":100,"time":80,"duty":150,"type":160,"description":600}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="w")

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
            for _, r in df.iterrows():
                d = r.get("date")
                t = r.get("time")
                self.tree.insert("", "end", values=(
                    d.strftime("%d.%m.%Y") if d else "",
                    t.strftime("%H:%M") if t else "",
                    r.get("duty",""),
                    r.get("type",""),
                    r.get("description",""),
                ))

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

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("960x600")

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
        CreateIncidentDialog(self, self.cfg, self.storage, self.telegram)

    def open_registry(self):
        RegistryWindow(self, self.storage)

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
