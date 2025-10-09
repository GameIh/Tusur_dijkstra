# graph_model.py
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional


@dataclass
class Vertex:
    vid: int
    name: str


@dataclass
class Edge:
    u: int
    v: int
    w: float


class Graph:
    def __init__(self, undirected: bool = True):
        self.undirected = undirected
        self.vertices: Dict[int, Vertex] = {}
        self.adj: Dict[int, Dict[int, float]] = {}
        self._name_to_vid: Dict[str, int] = {}
        self._next_vid = 1

    # ---- CRUD ----
    def add_vertex(self, name: Optional[str] = None) -> int:
        vid = self._next_vid
        self._next_vid += 1
        if name is None:
            name = f"V{vid}"
        self.vertices[vid] = Vertex(vid=vid, name=name)
        self._name_to_vid[name] = vid
        self.adj.setdefault(vid, {})
        return vid

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

    def clear(self):
        self.vertices.clear()
        self.adj.clear()
        self._name_to_vid.clear()
        self._next_vid = 1
