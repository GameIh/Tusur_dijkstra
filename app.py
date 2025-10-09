# app.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import simpledialog

from graph_model import Graph
from dijkstra import dijkstra
from canvas_view import GraphCanvas
from utils import COLORS


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Дейкстра — учебный проект (Tkinter)")
        self.geometry("1000x650")
        self.minsize(900, 600)

        # Модель
        self.graph = Graph(undirected=True)

        # Состояние
        self.mode = tk.StringVar(value="vertex")  # vertex | edge | move
        self.pending_from_vid = None  # для добавления ребра
        self.vertex_name_seq = 0

        # UI
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        # Верхняя панель
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Режим:").pack(side=tk.LEFT, padx=(0, 6))

        ttk.Radiobutton(toolbar, text="Добавить вершину", value="vertex",
                        variable=self.mode, command=self._on_mode_changed).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(toolbar, text="Добавить ребро", value="edge",
                        variable=self.mode, command=self._on_mode_changed).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(toolbar, text="Перемещать", value="move",
                        variable=self.mode, command=self._on_mode_changed).pack(side=tk.LEFT, padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.start_var = tk.StringVar(value="")
        self.end_var = tk.StringVar(value="")

        ttk.Label(toolbar, text="Старт:").pack(side=tk.LEFT)
        self.start_cb = ttk.Combobox(toolbar, width=6, textvariable=self.start_var, state="readonly")
        self.start_cb.pack(side=tk.LEFT, padx=4)

        ttk.Label(toolbar, text="Финиш:").pack(side=tk.LEFT)
        self.end_cb = ttk.Combobox(toolbar, width=6, textvariable=self.end_var, state="readonly")
        self.end_cb.pack(side=tk.LEFT, padx=4)

        ttk.Button(toolbar, text="Рассчитать путь", command=self.on_calculate).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="Сброс подсветки", command=self.on_clear_highlight).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Удалить всё", command=self.on_clear_all).pack(side=tk.LEFT, padx=(8, 0))

        # Поле результата
        bottom = ttk.Frame(self, padding=(10, 4))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(bottom, text="Результат:").pack(side=tk.LEFT)
        self.result_var = tk.StringVar(value="—")
        self.result_label = ttk.Label(bottom, textvariable=self.result_var, foreground=COLORS["accent"])
        self.result_label.pack(side=tk.LEFT, padx=8)

        # Канвас
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.gcanvas = GraphCanvas(self.canvas_frame,
                                   on_canvas_click=self.on_canvas_click,
                                   on_vertex_clicked=self.on_vertex_clicked,
                                   mode_provider=lambda: self.mode.get())
        self.gcanvas.pack(fill=tk.BOTH, expand=True)

        # Горячие клавиши
        self.bind("<Escape>", lambda e: self._reset_edge_add())
        self.bind("<Delete>", lambda e: self._delete_selection_hint())

        # Инициализация
        self._refresh_vertex_lists()

    # ---------- Колбэки Canvas ----------
    def on_canvas_click(self, x, y):
        if self.mode.get() == "vertex":
            name = self._next_vertex_name()
            vid = self.graph.add_vertex(name=name)
            self.gcanvas.draw_vertex(vid, name, x, y)
            self._refresh_vertex_lists()
        # В режимах edge/move клик по пустому месту ничего не делает

    def on_vertex_clicked(self, vid):
        mode = self.mode.get()
        if mode == "edge":
            if self.pending_from_vid is None:
                self.pending_from_vid = vid
                self.gcanvas.indicate_vertex_selected(vid)
            else:
                if vid == self.pending_from_vid:
                    # Клик по той же вершине — отмена выбора
                    self._reset_edge_add()
                    return
                # спросим вес
                weight = self._ask_weight()
                if weight is None:
                    return
                if self.graph.has_edge(self.pending_from_vid, vid):
                    messagebox.showwarning("Ребро уже есть",
                                           "Между этими вершинами ребро уже существует.")
                    self._reset_edge_add()
                    return

                self.graph.add_edge(self.pending_from_vid, vid, weight)
                self.gcanvas.draw_edge(self.pending_from_vid, vid, weight)
                self._reset_edge_add()

        # В режиме move обработка перетаскивания на стороне GraphCanvas

    # ---------- Действия ----------
    def on_calculate(self):
        self.gcanvas.clear_highlight()
        start_name = self.start_var.get()
        end_name = self.end_var.get()
        if not start_name or not end_name:
            messagebox.showinfo("Выбор вершин", "Выберите старт и финиш.")
            return
        if start_name == end_name:
            messagebox.showinfo("Один и тот же узел", "Старт и финиш совпадают.")
            return

        start_vid = self.graph.vertex_id_by_name(start_name)
        end_vid = self.graph.vertex_id_by_name(end_name)
        if start_vid is None or end_vid is None:
            messagebox.showerror("Ошибка", "Не удалось найти выбранные вершины.")
            return

        dist, path = dijkstra(self.graph.adj, start_vid, end_vid)
        if path is None:
            self.result_var.set("Пути нет.")
            return

        # Подсветим
        self.gcanvas.highlight_path(path)
        # Текст результата
        names = [self.graph.vertices[vid].name for vid in path]
        self.result_var.set(f"Длина = {dist:.3f}; путь: " + " → ".join(names))

    def on_clear_highlight(self):
        self.gcanvas.clear_highlight()
        self.result_var.set("—")

    def on_clear_all(self):
        if messagebox.askyesno("Очистить всё", "Удалить весь граф?"):
            self.pending_from_vid = None
            self.graph.clear()
            self.gcanvas.clear_all()
            self._refresh_vertex_lists()
            self.result_var.set("—")

    # ---------- Вспомогательные ----------
    def _ask_weight(self):
        try:
            value = simpledialog.askfloat("Вес ребра", "Введите неотрицательный вес:",
                                          minvalue=0.0, parent=self)
        except Exception:
            return None
        return value

    def _reset_edge_add(self):
        if self.pending_from_vid is not None:
            self.gcanvas.indicate_vertex_unselected(self.pending_from_vid)
        self.pending_from_vid = None

    def _refresh_vertex_lists(self):
        names = [v.name for v in self.graph.vertices.values()]
        self.start_cb["values"] = names
        self.end_cb["values"] = names
        # если пусто — сброс
        if self.start_var.get() not in names:
            self.start_var.set(names[0] if names else "")
        if self.end_var.get() not in names:
            self.end_var.set(names[0] if names else "")

    def _next_vertex_name(self):
        # A, B, C, ... Z, AA, AB ...
        n = self.vertex_name_seq
        self.vertex_name_seq += 1
        s = ""
        while True:
            s = chr(ord('A') + (n % 26)) + s
            n = n // 26 - 1
            if n < 0:
                break
        return s

    def _on_mode_changed(self):
        self._reset_edge_add()
        self.gcanvas.set_mode(self.mode.get())
        if self.mode.get() == "edge":
            self.result_var.set("Режим рёбер: кликните по двум вершинам, затем задайте вес.")
        elif self.mode.get() == "vertex":
            self.result_var.set("Режим вершин: кликайте по холсту, чтобы создать вершины.")
        else:
            self.result_var.set("Режим перемещения: перетаскивайте вершины мышью.")

    def _delete_selection_hint(self):
        # Заготовка для будущего удаления выделенного (можно расширить)
        pass


if __name__ == "__main__":
    App().mainloop()
