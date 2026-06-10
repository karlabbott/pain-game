#!/usr/bin/env python3
"""Compute force-directed minimap layouts for PAIN map JSON files.

Adds mapX/mapY (0.0-1.0) to every room in each map file.
These coordinates are used by the in-game fog-of-war minimap.

Usage:
  python tools/compute-map-layout.py              # all maps
  python tools/compute-map-layout.py pain5.json   # specific map
"""

import json
import math
import os
import random
import sys

MAPS_DIR = os.path.join(os.path.dirname(__file__), '..', 'maps')
SEED = 42
ITERATIONS = 300


def compute_layout(rooms):
    random.seed(SEED)
    nodes = {}
    for rm in rooms:
        nodes[rm['id']] = {'x': random.uniform(-1, 1), 'y': random.uniform(-1, 1)}

    # Deduplicate edges (treat directed connections as undirected for layout)
    edges = set()
    for rm in rooms:
        for d in rm.get('doors', []):
            a, b = rm['id'], d['target']
            if a in nodes and b in nodes:
                edges.add((min(a, b), max(a, b)))
    edges = list(edges)
    ids = list(nodes.keys())
    n = len(ids)

    for iteration in range(ITERATIONS):
        temp = 1.0 - iteration / ITERATIONS
        forces = {nid: [0.0, 0.0] for nid in ids}

        # Repulsion between all node pairs
        k_rep = 0.5
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                dx = nodes[a]['x'] - nodes[b]['x']
                dy = nodes[a]['y'] - nodes[b]['y']
                dist = max(math.hypot(dx, dy), 0.01)
                f = k_rep / (dist * dist)
                fx, fy = f * dx / dist, f * dy / dist
                forces[a][0] += fx; forces[a][1] += fy
                forces[b][0] -= fx; forces[b][1] -= fy

        # Attraction along edges
        k_att = 0.05
        ideal = 0.3
        for a, b in edges:
            dx = nodes[b]['x'] - nodes[a]['x']
            dy = nodes[b]['y'] - nodes[a]['y']
            dist = max(math.hypot(dx, dy), 0.01)
            f = k_att * (dist - ideal)
            fx, fy = f * dx / dist, f * dy / dist
            forces[a][0] += fx; forces[a][1] += fy
            forces[b][0] -= fx; forces[b][1] -= fy

        # Apply forces with cooling
        max_disp = 0.1 * temp + 0.005
        for nid in ids:
            fx, fy = forces[nid]
            dx2 = min(max_disp, abs(fx)) * (1 if fx > 0 else -1)
            dy2 = min(max_disp, abs(fy)) * (1 if fy > 0 else -1)
            nodes[nid]['x'] += dx2
            nodes[nid]['y'] += dy2

    # Normalize to 0.0-1.0
    xs = [nodes[nid]['x'] for nid in ids]
    ys = [nodes[nid]['y'] for nid in ids]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    rx = max_x - min_x if max_x != min_x else 1
    ry = max_y - min_y if max_y != min_y else 1
    for nid in ids:
        nodes[nid]['x'] = round((nodes[nid]['x'] - min_x) / rx, 3)
        nodes[nid]['y'] = round((nodes[nid]['y'] - min_y) / ry, 3)

    return nodes


def process_map(mapfile):
    path = os.path.join(MAPS_DIR, mapfile)
    with open(path, 'r') as f:
        data = json.load(f)

    layout = compute_layout(data['rooms'])
    for rm in data['rooms']:
        if rm['id'] in layout:
            rm['mapX'] = layout[rm['id']]['x']
            rm['mapY'] = layout[rm['id']]['y']

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

    print(mapfile + ': ' + str(len(data['rooms'])) + ' rooms laid out')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for mf in sys.argv[1:]:
            process_map(mf)
    else:
        index_path = os.path.join(MAPS_DIR, 'index.json')
        with open(index_path) as f:
            maps = json.load(f)
        for mf in maps:
            process_map(mf)
