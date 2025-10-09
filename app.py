# app.py
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

from graph_model import Graph
from dijkstra import dijkstra
from canvas_view import GraphCanvas
from utils import COLORS


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Алгоритм Дейкстра")
        self.geometry("1000x650")
        self.minsize(900, 600)

        self.graph = Graph(undirected=True)

        self.mode = tk.StringVar(value="vertex")
        self.pending_from_vid = None
        self.vertex_name_seq = 0

        self._build_ui()

    def _build_ui(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый граф", command=self.on_clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Открыть…", command=self.on_load)
        file_menu.add_command(label="Сохранить как…", command=self.on_save_as)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

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

        bottom = ttk.Frame(self, padding=(10, 4))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(bottom, text="Результат:").pack(side=tk.LEFT)
        self.result_var = tk.StringVar(value="—")
        self.result_label = ttk.Label(bottom, textvariable=self.result_var, foreground=COLORS["accent"])
        self.result_label.pack(side=tk.LEFT, padx=8)

        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.gcanvas = GraphCanvas(
            self.canvas_frame,
            on_canvas_click=self.on_canvas_click,
            on_vertex_clicked=self.on_vertex_clicked,
            mode_provider=lambda: self.mode.get(),
            on_request_delete_vertex=self._delete_vertex,
            on_request_delete_edge=self._delete_edge,
            on_request_update_weight=self._update_edge_weight,
            ask_weight=self._ask_weight
        )
        self.gcanvas.pack(fill=tk.BOTH, expand=True)

        self.bind("<Escape>", lambda e: self._reset_edge_add())

        self._refresh_vertex_lists()

    def on_canvas_click(self, x, y):
        if self.mode.get() == "vertex":
            name = self._next_vertex_name()
            vid = self.graph.add_vertex(name=name)
            self.gcanvas.draw_vertex(vid, name, x, y)
            self._refresh_vertex_lists()

    def on_vertex_clicked(self, vid):
        mode = self.mode.get()
        if mode == "edge":
            if self.pending_from_vid is None:
                self.pending_from_vid = vid
                self.gcanvas.indicate_vertex_selected(vid)
            else:
                if vid == self.pending_from_vid:
                    self._reset_edge_add()
                    return
                weight = self._ask_weight()
                if weight is None:
                    return
                if self.graph.has_edge(self.pending_from_vid, vid):
                    messagebox.showwarning("Ребро уже есть", "Между этими вершинами ребро уже существует.")
                    self._reset_edge_add()
                    return
                self.graph.add_edge(self.pending_from_vid, vid, weight)
                self.gcanvas.draw_edge(self.pending_from_vid, vid, weight)
                self._reset_edge_add()

    def _delete_vertex(self, vid: int):
        removed = self.graph.remove_vertex(vid)
        if not self.graph.vertices:
            self.vertex_name_seq = 0
        self.result_var.set(f"Удалена вершина; удалено рёбер: {len(removed)}")
        self._refresh_vertex_lists()

    def _delete_edge(self, u: int, v: int):
        self.graph.remove_edge(u, v)
        self.result_var.set("Ребро удалено.")

    def _update_edge_weight(self, u: int, v: int, w: float):
        try:
            self.graph.update_edge_weight(u, v, w)
            self.result_var.set(f"Вес ребра обновлён: {w:g}")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))

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

        self.gcanvas.highlight_path(path)
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
            self.vertex_name_seq = 0
            self._refresh_vertex_lists()
            self.result_var.set("—")

    def on_save_as(self):
        if not self.graph.vertices:
            messagebox.showinfo("Сохранение", "Граф пуст — сохранять нечего.")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить граф",
            defaultextension=".json",
            filetypes=[("Graph JSON", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        data = {
            "format": "dijkstra_tk_v1",
            "undirected": self.graph.undirected,
            "vertices": [
                {
                    "vid": vid,
                    "name": v.name,
                    "x": float(self.gcanvas.vertex_positions.get(vid, (0, 0))[0]),
                    "y": float(self.gcanvas.vertex_positions.get(vid, (0, 0))[1]),
                }
                for vid, v in self.graph.vertices.items()
            ],
            "edges": self._collect_edges_for_save(),
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.result_var.set(f"Сохранено: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

    def _collect_edges_for_save(self):
        edges = []
        seen = set()
        for u, nbrs in self.graph.adj.items():
            for v, w in nbrs.items():
                key = (min(u, v), max(u, v)) if self.graph.undirected else (u, v)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"u": key[0], "v": key[1] if self.graph.undirected else v, "w": w})
        return edges

    def on_load(self):
        path = filedialog.askopenfilename(
            title="Открыть граф",
            filetypes=[("Graph JSON", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return

        try:
            self._load_from_dict(data)
            self.result_var.set(f"Загружено: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка формата", str(e))

    def _load_from_dict(self, data: dict):
        if data.get("format") != "dijkstra_tk_v1":
            raise ValueError("Неверный или неподдерживаемый формат файла.")
        undirected = bool(data.get("undirected", True))

        self.pending_from_vid = None
        self.graph = Graph(undirected=undirected)
        self.gcanvas.clear_all()

        id_to_name = {}
        for item in data.get("vertices", []):
            vid = int(item["vid"])
            name = str(item["name"])
            x = float(item.get("x", 0))
            y = float(item.get("y", 0))
            self.graph.add_vertex_explicit(vid, name)
            self.gcanvas.draw_vertex(vid, name, x, y)
            id_to_name[vid] = name

        for e in data.get("edges", []):
            u = int(e["u"])
            v = int(e["v"])
            w = float(e["w"])
            if not self.graph.has_edge(u, v):
                self.graph.add_edge(u, v, w)
                self.gcanvas.draw_edge(u, v, w)

        self._refresh_vertex_lists()
        self.vertex_name_seq = self._next_seq_from_existing_names()

    def _ask_weight(self):
        try:
            return simpledialog.askfloat("Вес ребра", "Введите неотрицательный вес:", minvalue=0.0, parent=self)
        except Exception:
            return None

    def _reset_edge_add(self):
        if self.pending_from_vid is not None:
            self.gcanvas.indicate_vertex_unselected(self.pending_from_vid)
        self.pending_from_vid = None

    def _refresh_vertex_lists(self):
        names = [v.name for v in self.graph.vertices.values()]
        self.start_cb["values"] = names
        self.end_cb["values"] = names
        if self.start_var.get() not in names:
            self.start_var.set(names[0] if names else "")
        if self.end_var.get() not in names:
            self.end_var.set(names[0] if names else "")

    def _next_vertex_name(self):
        n = self.vertex_name_seq
        self.vertex_name_seq += 1
        s = ""
        while True:
            s = chr(ord('A') + (n % 26)) + s
            n = n // 26 - 1
            if n < 0:
                break
        return s

    def _name_to_index(self, name: str) -> int:
        idx = 0
        for ch in name:
            if not ('A' <= ch <= 'Z'):
                return -1
            idx = idx * 26 + (ord(ch) - ord('A') + 1)
        return idx - 1

    def _next_seq_from_existing_names(self) -> int:
        if not self.graph.vertices:
            return 0
        mx = -1
        for v in self.graph.vertices.values():
            mx = max(mx, self._name_to_index(v.name))
        return (mx + 1) if mx >= 0 else 0

    def _on_mode_changed(self):
        self._reset_edge_add()
        self.gcanvas.set_mode(self.mode.get())
        if self.mode.get() == "edge":
            self.result_var.set("Режим рёбер: кликните по двум вершинам, затем задайте вес. ПКМ по ребру — меню.")
        elif self.mode.get() == "vertex":
            self.result_var.set("Режим вершин: кликайте по холсту, чтобы создать вершины. ПКМ по вершине — удалить.")
        else:
            self.result_var.set("Режим перемещения: перетаскивайте вершины мышью.")


if __name__ == "__main__":
    App().mainloop()
