import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Callable, Dict, Tuple, Optional, List
from utils import COLORS

RADIUS = 18


class GraphCanvas(ttk.Frame):
    def __init__(self, master,
                 on_canvas_click: Callable[[int, int], None],
                 on_vertex_clicked: Callable[[int], None],
                 mode_provider: Callable[[], str],
                 on_request_delete_vertex: Callable[[int], None] = lambda vid: None,
                 on_request_delete_edge: Callable[[int, int], None] = lambda u, v: None,
                 on_request_update_weight: Callable[[int, int, float], None] = lambda u, v, w: None,
                 ask_weight: Callable[[], Optional[float]] = lambda: None):
        super().__init__(master)
        self.on_canvas_click = on_canvas_click
        self.on_vertex_clicked = on_vertex_clicked
        self.mode_provider = mode_provider

        self.on_request_delete_vertex = on_request_delete_vertex
        self.on_request_delete_edge = on_request_delete_edge
        self.on_request_update_weight = on_request_update_weight
        self.ask_weight = ask_weight

        self.canvas = tk.Canvas(self, bg=COLORS["canvas_bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.vertex_items: Dict[int, Tuple[int, int]] = {}
        self.vertex_positions: Dict[int, Tuple[float, float]] = {}
        self.edge_items: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.selected_vid: Optional[int] = None

        self.dragging_vid: Optional[int] = None
        self.drag_offset: Tuple[float, float] = (0, 0)

        self.vertex_menu = tk.Menu(self, tearoff=0)
        self.vertex_menu.add_command(label="Удалить вершину", command=self._cm_delete_vertex)

        self.edge_menu = tk.Menu(self, tearoff=0)
        self.edge_menu.add_command(label="Изменить вес…", command=self._cm_edit_weight)
        self.edge_menu.add_command(label="Удалить ребро", command=self._cm_delete_edge)

        self._cm_vertex_vid: Optional[int] = None
        self._cm_edge_uv: Optional[Tuple[int, int]] = None

        self.canvas.bind("<Button-1>", self._on_lmb_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_lmb_up)
        self.canvas.bind("<Button-3>", self._on_rmb)
        self.canvas.bind("<Double-Button-1>", self._on_double_lmb)

    def draw_vertex(self, vid: int, name: str, x: float, y: float):
        circle = self.canvas.create_oval(x - RADIUS, y - RADIUS, x + RADIUS, y + RADIUS,
                                         fill=COLORS["node_fill"], outline=COLORS["node_border"],
                                         width=2, tags=(f"vertex", f"v{vid}"))
        text = self.canvas.create_text(x, y, text=name, font=("Segoe UI", 10, "bold"),
                                       fill=COLORS["node_text"],
                                       tags=(f"vertex_label", f"v{vid}"))
        self.vertex_items[vid] = (circle, text)
        self.vertex_positions[vid] = (x, y)

        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("vertex_label")

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
                                        tags=("edge_label", f"e{u}-{v}", f"e{v}-{u}"))
        self.edge_items[(u, v)] = (line, label)
        self.edge_items[(v, u)] = (line, label)

        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("vertex_label")

    def move_vertex_to(self, vid: int, x: float, y: float):
        circle, text = self.vertex_items[vid]
        x0, y0 = self.vertex_positions[vid]
        dx, dy = x - x0, y - y0
        self.canvas.move(circle, dx, dy)
        self.canvas.move(text, dx, dy)
        self.vertex_positions[vid] = (x, y)
        self._redraw_incident_edges(vid)

        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("vertex_label")

    def _redraw_incident_edges(self, vid: int):
        for (u, v), (line, label) in list(self.edge_items.items()):
            if u == vid or v == vid:
                x1, y1 = self.vertex_positions[u]
                x2, y2 = self.vertex_positions[v]
                self.canvas.coords(line, x1, y1, x2, y2)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.coords(label, mx, my - 10)

    def highlight_path(self, path: List[int]):
        self.clear_highlight()
        for vid in path:
            circle, _ = self.vertex_items[vid]
            self.canvas.itemconfig(circle, fill=COLORS["node_fill_active"], outline=COLORS["accent"], width=3)
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if (u, v) in self.edge_items:
                line, _ = self.edge_items[(u, v)]
                self.canvas.itemconfig(line, width=4, fill=COLORS["accent"])

        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("vertex_label")

    def clear_highlight(self):
        for vid, (circle, _) in self.vertex_items.items():
            self.canvas.itemconfig(circle, fill=COLORS["node_fill"], outline=COLORS["node_border"], width=2)
        for (u, v), (line, _) in self.edge_items.items():
            self.canvas.itemconfig(line, width=2, fill=COLORS["edge"])

    def indicate_vertex_selected(self, vid: int):
        self.selected_vid = vid
        circle, _ = self.vertex_items[vid]
        self.canvas.itemconfig(circle, outline=COLORS["select"], width=3)

    def indicate_vertex_unselected(self, vid: int):
        if self.selected_vid == vid:
            self.selected_vid = None
        circle, _ = self.vertex_items[vid]
        self.canvas.itemconfig(circle, outline=COLORS["node_border"], width=2)

    def clear_all(self):
        self.canvas.delete("all")
        self.vertex_items.clear()
        self.vertex_positions.clear()
        self.edge_items.clear()
        self.selected_vid = None

    def set_mode(self, mode: str):
        pass

    def _on_lmb_down(self, e):
        mode = self.mode_provider()
        item = self._item_under_cursor(e.x, e.y)
        if item and "vertex" in self.canvas.gettags(item):
            vid = self._vid_from_tags(self.canvas.gettags(item))
            if mode == "move":
                self.dragging_vid = vid
                x, y = self.vertex_positions[vid]
                self.drag_offset = (e.x - x, e.y - y)
            else:
                self.on_vertex_clicked(vid)
        else:
            if mode == "vertex":
                self.on_canvas_click(e.x, e.y)

    def _on_mouse_move(self, e):
        if self.dragging_vid is not None and self.mode_provider() == "move":
            vx = e.x - self.drag_offset[0]
            vy = e.y - self.drag_offset[1]
            self.move_vertex_to(self.dragging_vid, vx, vy)

    def _on_lmb_up(self, e):
        self.dragging_vid = None

    def _on_rmb(self, e):
        item = self._item_under_cursor(e.x, e.y)
        if not item:
            return
        tags = self.canvas.gettags(item)
        if "vertex" in tags:
            vid = self._vid_from_tags(tags)
            if vid is not None:
                self._cm_vertex_vid = vid
                try:
                    self.vertex_menu.tk_popup(e.x_root, e.y_root)
                finally:
                    self.vertex_menu.grab_release()
        elif "edge" in tags or "edge_label" in tags:
            uv = self._edge_uv_from_tags(tags)
            if uv:
                self._cm_edge_uv = uv
                try:
                    self.edge_menu.tk_popup(e.x_root, e.y_root)
                finally:
                    self.edge_menu.grab_release()

    def _on_double_lmb(self, e):
        item = self._item_under_cursor(e.x, e.y)
        if not item:
            return
        tags = self.canvas.gettags(item)
        if "edge" in tags or "edge_label" in tags:
            uv = self._edge_uv_from_tags(tags)
            if not uv:
                return
            u, v = uv
            new_w = self.ask_weight()
            if new_w is None:
                return
            self.on_request_update_weight(u, v, new_w)
            self._update_edge_label(u, v, f"{new_w:g}")

    def _cm_delete_vertex(self):
        if self._cm_vertex_vid is None:
            return
        vid = self._cm_vertex_vid
        self._cm_vertex_vid = None
        self.on_request_delete_vertex(vid)
        self._remove_vertex_visual(vid)

    def _cm_edit_weight(self):
        if not self._cm_edge_uv:
            return
        u, v = self._cm_edge_uv
        self._cm_edge_uv = None
        new_w = self.ask_weight()
        if new_w is None:
            return
        self.on_request_update_weight(u, v, new_w)
        self._update_edge_label(u, v, f"{new_w:g}")

    def _cm_delete_edge(self):
        if not self._cm_edge_uv:
            return
        u, v = self._cm_edge_uv
        self._cm_edge_uv = None
        self.on_request_delete_edge(u, v)
        self._remove_edge_visual(u, v)

    def _remove_vertex_visual(self, vid: int):
        for (u, v) in list(self.edge_items.keys()):
            if u == vid or v == vid:
                self._remove_edge_visual(u, v)
        if vid in self.vertex_items:
            circle, text = self.vertex_items.pop(vid)
            self.canvas.delete(circle)
            self.canvas.delete(text)
        self.vertex_positions.pop(vid, None)

    def _remove_edge_visual(self, u: int, v: int):
        if (u, v) in self.edge_items:
            line, label = self.edge_items.pop((u, v))
            self.edge_items.pop((v, u), None)
            self.canvas.delete(line)
            self.canvas.delete(label)

    def _update_edge_label(self, u: int, v: int, text: str):
        if (u, v) in self.edge_items:
            _, label = self.edge_items[(u, v)]
            self.canvas.itemconfig(label, text=text)

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

    @staticmethod
    def _edge_uv_from_tags(tags) -> Optional[Tuple[int, int]]:
        for t in tags:
            if t.startswith("e"):
                try:
                    pair = t[1:]
                    u_str, v_str = pair.split("-", 1)
                    u, v = int(u_str), int(v_str)
                    return (u, v)
                except Exception:
                    continue
        return None
