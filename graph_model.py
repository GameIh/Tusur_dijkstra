# graph_model.py
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple


@dataclass
class Vertex:
    vid: int
    name: str


class Graph:
    def __init__(self, undirected: bool = True):
        self.undirected = undirected
        self.vertices: Dict[int, Vertex] = {}
        self.adj: Dict[int, Dict[int, float]] = {}
        self._name_to_vid: Dict[str, int] = {}
        self._next_vid = 1

    def add_vertex(self, name: Optional[str] = None) -> int:
        vid = self._next_vid
        self._next_vid += 1
        if name is None:
            name = f"V{vid}"
        self.vertices[vid] = Vertex(vid=vid, name=name)
        self._name_to_vid[name] = vid
        self.adj.setdefault(vid, {})
        return vid

    def add_vertex_explicit(self, vid: int, name: str):
        self.vertices[vid] = Vertex(vid=vid, name=name)
        self._name_to_vid[name] = vid
        self.adj.setdefault(vid, {})
        if vid >= self._next_vid:
            self._next_vid = vid + 1

    def add_edge(self, u: int, v: int, w: float):
        if u not in self.vertices or v not in self.vertices:
            raise ValueError("Вершина не существует.")
        if w < 0:
            raise ValueError("Вес не может быть отрицательным.")
        self.adj.setdefault(u, {})[v] = w
        if self.undirected:
            self.adj.setdefault(v, {})[u] = w

    def has_edge(self, u: int, v: int) -> bool:
        return u in self.adj and v in self.adj[u]

    def vertex_id_by_name(self, name: str) -> Optional[int]:
        return self._name_to_vid.get(name)

    def update_edge_weight(self, u: int, v: int, w: float):
        if w < 0:
            raise ValueError("Вес не может быть отрицательным.")
        if not self.has_edge(u, v):
            raise ValueError("Ребра не существует.")
        self.adj[u][v] = w
        if self.undirected:
            self.adj[v][u] = w

    def remove_edge(self, u: int, v: int):
        if self.has_edge(u, v):
            del self.adj[u][v]
        if self.undirected and v in self.adj and u in self.adj[v]:
            del self.adj[v][u]

    def remove_vertex(self, vid: int) -> List[Tuple[int, int]]:
        if vid not in self.vertices:
            return []
        name = self.vertices[vid].name
        self._name_to_vid.pop(name, None)

        removed_edges: List[Tuple[int, int]] = []
        for v in list(self.adj.get(vid, {}).keys()):
            removed_edges.append((vid, v))
            if self.undirected:
                self.adj[v].pop(vid, None)
        self.adj.pop(vid, None)

        for u in list(self.adj.keys()):
            if vid in self.adj[u]:
                removed_edges.append((u, vid))
                self.adj[u].pop(vid, None)

        del self.vertices[vid]
        return removed_edges

    def clear(self):
        self.vertices.clear()
        self.adj.clear()
        self._name_to_vid.clear()
        self._next_vid = 1
