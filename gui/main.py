# gui/main.py
import tkinter as tk
from tkinter import ttk, messagebox
import httpx
from tkintermapview import TkinterMapView
import json
import webbrowser


def load_courts_data(file_path="data/courts_rostov.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    courts = data if isinstance(data, list) else data.get("courts", [])
    for court in courts:
        if "coordinates" in court:
            court["latitude"] = court["coordinates"]["lat"]
            court["longitude"] = court["coordinates"]["lon"]
        court["polygon"] = court.get("polygon", "")
    return courts


class CourtFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("600x400")
        self.root.title("Поиск суда")

        self.courts = load_courts_data()
        self.address_database = [court["address"] for court in self.courts]

        tk.Label(root, text="Адрес должника:").grid(row=0, column=0, padx=10, pady=10)
        self.address_entry = tk.Entry(root, width=50)
        self.address_entry.grid(row=0, column=1, padx=10, pady=5)
        self.address_entry.bind("<KeyRelease>", self.update_suggestions)
        self.address_entry.bind("<FocusOut>", lambda e: self.root.after(200, self.hide_suggestions))
        self.address_entry.bind("<Down>", self.focus_suggestions)

        self.suggestion_listbox = None

        tk.Label(root, text="Сумма должника:").grid(row=1, column=0, padx=10, pady=10)
        self.debt_amount_entry = tk.Entry(root, width=20)
        self.debt_amount_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        tk.Label(root, text="Категория дел:").grid(row=2, column=0, padx=10, pady=10)
        self.case_type_combo = ttk.Combobox(root, values=[
            "имущественный_спор", "расторжение_брака", "алименты", "раздел_имущества"
        ], width=47)
        self.case_type_combo.grid(row=2, column=1, padx=10, pady=10)
        self.case_type_combo.set("имущественный_спор")

        tk.Button(root, text="Найти суд", command=self.find_court).grid(row=3, column=0, columnspan=2, pady=10)

        self.result_text = tk.Text(root, height=10, width=70)
        self.result_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        self.map_frame = tk.Frame(root)

        self.result_text.tag_configure("link", foreground="blue", underline=1)
        self.result_text.tag_bind("link", "<Button-1>", self.open_website)

    def update_suggestions(self, event):
        query = self.address_entry.get().strip().lower()
        if not query:
            self.hide_suggestions()
            return
        suggestions = [addr for addr in self.address_database if query in addr.lower()][:5]
        if not suggestions:
            self.hide_suggestions()
            return
        self.hide_suggestions()
        self.suggestion_listbox = tk.Listbox(self.root, height=min(len(suggestions), 5), width=50)
        for suggestion in suggestions:
            self.suggestion_listbox.insert(tk.END, suggestion)
        x = self.address_entry.winfo_x() + 10
        y = self.address_entry.winfo_y() + self.address_entry.winfo_height() + 1
        self.suggestion_listbox.place(x=x, y=y)
        self.suggestion_listbox.lift()
        self.suggestion_listbox.bind("<Button-1>", self.select_suggestion)
        self.suggestion_listbox.bind("<Double-Button-1>", self.select_suggestion)
        self.suggestion_listbox.bind("<Return>", self.select_suggestion)
        self.suggestion_listbox.bind("<Escape>", lambda e: self.hide_suggestions())

    def focus_suggestions(self, event):
        if self.suggestion_listbox:
            self.suggestion_listbox.focus_set()
            self.suggestion_listbox.select_set(0)

    def select_suggestion(self, event):
        if self.suggestion_listbox:
            if event.type == "4":  # Button-1
                index = self.suggestion_listbox.nearest(event.y)
                self.suggestion_listbox.select_clear(0, tk.END)
                self.suggestion_listbox.select_set(index)
            if self.suggestion_listbox.curselection():
                selected = self.suggestion_listbox.get(self.suggestion_listbox.curselection())
                self.address_entry.delete(0, tk.END)
                self.address_entry.insert(0, selected)
                self.hide_suggestions()
                self.address_entry.focus_set()

    def hide_suggestions(self, event=None):
        if self.suggestion_listbox:
            self.suggestion_listbox.destroy()
            self.suggestion_listbox = None

    def open_website(self, event):
        index = self.result_text.index("@%s,%s" % (event.x, event.y))
        tag_ranges = self.result_text.tag_ranges("link")
        if not tag_ranges:
            return
        for start, end in zip(tag_ranges[0::2], tag_ranges[1::2]):
            if self.result_text.compare(start, "<=", index) and self.result_text.compare(end, ">=", index):
                url = self.result_text.get(start, end)
                if url:
                    webbrowser.open(url)
                break

    def find_court(self):
        address = self.address_entry.get().strip()
        debt_amount = self.debt_amount_entry.get().strip()
        case_type = self.case_type_combo.get()

        if not address:
            messagebox.showerror("Ошибка", "Введите адрес")
            return
        try:
            debt_amount = float(debt_amount) if debt_amount else 0.0
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму")
            return

        api_url = "http://localhost:8000/api/courts/find_court/"
        payload = {"address": address, "debt_amount": debt_amount, "case_type": case_type}
        try:
            with httpx.Client() as client:
                response = client.post(api_url, json=payload, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                print(f"Ответ бэкенда: {result}")

                if result.get("status") == "error":
                    raise ValueError(result.get("detail", "Суд не найден"))

                court = result.get("court")
                if not court:
                    raise ValueError("Бэкенд не вернул данные о суде")

                self.result_text.delete(1.0, tk.END)
                result_str = (f"Название: {court['name']}\n"
                              f"Тип: {court.get('type', 'Не указан')}\n"
                              f"Адрес: {court.get('address', 'Не указан')}\n"
                              f"Телефон: {court.get('phone', 'Не указан')}\n"
                              f"Email: {court.get('email', 'Не указан')}\n"
                              f"Электронная подача: {court.get('electronic_filing', 'Не указана')}\n"  # Бэкенд теперь возвращает
                              f"Сайт: ")
                self.result_text.insert(tk.END, result_str)

                website = court.get('website', 'Не указан')
                if website != 'Не указан':
                    self.result_text.insert(tk.END, website, "link")
                else:
                    self.result_text.insert(tk.END, website)
                self.result_text.insert(tk.END, "\n")

                if "latitude" in court and "longitude" in court and court["latitude"] and court["longitude"]:
                    self.show_court_map(court["latitude"], court["longitude"], court["name"])
                else:
                    self.hide_map()
                    messagebox.showwarning("Предупреждение", "Координаты суда не найдены")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось найти суд: {str(e)}")
            self.hide_map()

    def show_court_map(self, lat: float, lon: float, court_name: str):
        print(f"Отображаем карту: lat={lat}, lon={lon}, name={court_name}")
        self.map_frame.destroy()
        self.map_frame = tk.Frame(self.root)
        self.map_widget = TkinterMapView(self.map_frame, width=600, height=400)
        self.map_widget.pack(side=tk.BOTTOM)
        self.map_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10)
        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(15)
        self.map_widget.set_marker(lat, lon, text=court_name, marker_color_circle="red", marker_color_outside="black")
        self.hide_map_button = tk.Button(self.map_frame, text="Скрыть карту", command=self.hide_map)
        self.hide_map_button.pack(side=tk.TOP, pady=5)
        self.root.geometry("600x800")

    def hide_map(self):
        self.map_frame.grid_forget()
        if hasattr(self, 'hide_map_button'):
            self.hide_map_button.destroy()
        self.root.geometry("600x400")


if __name__ == "__main__":
    root = tk.Tk()
    app = CourtFinderApp(root)
    root.mainloop()