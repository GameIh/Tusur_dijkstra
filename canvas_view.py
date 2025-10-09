# canvas_view.py
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Tuple, Optional, List
from utils import COLORS

RADIUS = 18


class GraphCanvas(ttk.Frame):
    def __init__(self, master,
                 on_canvas_click: Callable[[int, int], None],
                 on_vertex_clicked: Callable[[int], None],
                 mode_provider: Callable[[], str]):
        super().__init__(master)
        self.on_canvas_click = on_canvas_click
        self.on_vertex_clicked = on_vertex_clicked
        self.mode_provider = mode_provider

        self.canvas = tk.Canvas(self, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # хранение координат/элементов
        self.vertex_items: Dict[int, Tuple[int, int]] = {}  # vid -> (circle_id, text_id)
        self.vertex_positions: Dict[int, Tuple[float, float]] = {}  # vid -> (x, y)
        self.edge_items: Dict[Tuple[int, int], Tuple[int, int]] = {}  # (u,v)->(line_id, text_id)
        self.selected_vid: Optional[int] = None

        # перетаскивание
        self.dragging_vid: Optional[int] = None
        self.drag_offset: Tuple[float, float] = (0, 0)

        # биндинги
        self.canvas.bind("<Button-1>", self._on_lmb_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_lmb_up)
        self.canvas.bind("<Configure>", lambda e: None)

    # ---------- Рисование вершин/рёбер ----------
    def draw_vertex(self, vid: int, name: str, x: float, y: float):
        circle = self.canvas.create_oval(x - RADIUS, y - RADIUS, x + RADIUS, y + RADIUS,
                                         fill=COLORS["node_fill"], outline=COLORS["node_border"],
                                         width=2, tags=(f"vertex", f"v{vid}"))
        text = self.canvas.create_text(x, y, text=name, font=("Segoe UI", 10, "bold"),
                                       fill=COLORS["node_text"],
                                       tags=(f"vertex_label", f"v{vid}"))
        self.vertex_items[vid] = (circle, text)
        self.vertex_positions[vid] = (x, y)

    def draw_edge(self, u: int, v: int, w: float):
        x1, y1 = self.vertex_positions[u]
        x2, y2 = self.vertex_positions[v]
        line = self.canvas.create_line(x1, y1, x2, y2, width=2,
                                       fill=COLORS["edge"],
                                       tags=(f"edge", f"e{u}-{v}", f"e{v}-{u}"))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = self.canvas.create_text(mx, my - 10, text=f"{w:g}",
                                        font=("Segoe UI", 9),
                                        fill=COLORS["edge_text"],
                                        tags=("edge_label",))
        self.edge_items[(u, v)] = (line, label)
        self.edge_items[(v, u)] = (line, label)  # для удобства поиска

    def move_vertex_to(self, vid: int, x: float, y: float):
        circle, text = self.vertex_items[vid]
        x0, y0 = self.vertex_positions[vid]
        dx, dy = x - x0, y - y0
        self.canvas.move(circle, dx, dy)
        self.canvas.move(text, dx, dy)
        self.vertex_positions[vid] = (x, y)
        # перерисовать рёбра, где участвует vid
        self._redraw_incident_edges(vid)

    def _redraw_incident_edges(self, vid: int):
        for (u, v), (line, label) in list(self.edge_items.items()):
            if u == vid or v == vid:
                x1, y1 = self.vertex_positions[u]
                x2, y2 = self.vertex_positions[v]
                self.canvas.coords(line, x1, y1, x2, y2)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.coords(label, mx, my - 10)

    # ---------- Подсветка ----------
    def highlight_path(self, path: List[int]):
        self.clear_highlight()
        # подсветим вершины
        for vid in path:
            circle, _ = self.vertex_items[vid]
            self.canvas.itemconfig(circle, fill=COLORS["node_fill_active"], outline=COLORS["accent"], width=3)

        # подсветим рёбра на пути
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if (u, v) in self.edge_items:
                line, _ = self.edge_items[(u, v)]
                self.canvas.itemconfig(line, width=4, fill=COLORS["accent"])

    def clear_highlight(self):
        for vid, (circle, _) in self.vertex_items.items():
            self.canvas.itemconfig(circle, fill=COLORS["node_fill"], outline=COLORS["node_border"], width=2)
        for (u, v), (line, _) in self.edge_items.items():
            self.canvas.itemconfig(line, width=2, fill=COLORS["edge"])

    # ---------- Выделение при добавлении ребра ----------
    def indicate_vertex_selected(self, vid: int):
        self.selected_vid = vid
        circle, _ = self.vertex_items[vid]
        self.canvas.itemconfig(circle, outline=COLORS["select"], width=3)

    def indicate_vertex_unselected(self, vid: int):
        if self.selected_vid == vid:
            self.selected_vid = None
        circle, _ = self.vertex_items[vid]
        self.canvas.itemconfig(circle, outline=COLORS["node_border"], width=2)

    # ---------- Сбрасы и очистка ----------
    def clear_all(self):
        self.canvas.delete("all")
        self.vertex_items.clear()
        self.vertex_positions.clear()
        self.edge_items.clear()
        self.selected_vid = None

    def set_mode(self, mode: str):
        # визуально подсказок не даём здесь; поведение меняется в обработчиках
        pass

    # ---------- Обработчики мыши ----------
    def _on_lmb_down(self, e):
        mode = self.mode_provider()
        item = self._item_under_cursor(e.x, e.y)
        if item and "vertex" in self.canvas.gettags(item):
            # клик по вершине
            vid = self._vid_from_tags(self.canvas.gettags(item))
            if mode == "move":
                # начать перетаскивание
                self.dragging_vid = vid
                x, y = self.vertex_positions[vid]
                self.drag_offset = (e.x - x, e.y - y)
            else:
                self.on_vertex_clicked(vid)
        else:
            # клик по пустому месту
            if mode == "vertex":
                self.on_canvas_click(e.x, e.y)

    def _on_mouse_move(self, e):
        if self.dragging_vid is not None and self.mode_provider() == "move":
            vx = e.x - self.drag_offset[0]
            vy = e.y - self.drag_offset[1]
            self.move_vertex_to(self.dragging_vid, vx, vy)

    def _on_lmb_up(self, e):
        self.dragging_vid = None

    # ---------- Вспомогательные ----------
    def _item_under_cursor(self, x, y):
        items = self.canvas.find_overlapping(x, y, x, y)
        return items[-1] if items else None

    @staticmethod
    def _vid_from_tags(tags) -> Optional[int]:
        for t in tags:
            if t.startswith("v"):
                try:
                    return int(t[1:])
                except ValueError:
                    continue
        return None
