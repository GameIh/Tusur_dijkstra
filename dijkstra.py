# dijkstra.py
import heapq
from typing import Dict, Tuple, Optional, List


def dijkstra(adj: Dict[int, Dict[int, float]],
             start: int,
             goal: int) -> Tuple[float, Optional[List[int]]]:
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]

    visited = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == goal:
            path = [u]
            while u in prev:
                u = prev[u]
                path.append(u)
            path.reverse()
            return d, path

        for v, w in adj.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    return float("inf"), None
