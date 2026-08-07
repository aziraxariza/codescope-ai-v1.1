"""
Architecture diagram generator.
Queries Neo4j for cross-file CALLS relationships and converts them into
a Mermaid.js graph string, grouped into subgraphs by top-level directory
so the result reads as an architecture map rather than a tangle of files.

The frontend renders the Mermaid string client-side —
no extra infrastructure needed.
"""

import os
import re

from ..graph.neo4j_client import GraphDB

_db = GraphDB()

REPO_PATH = os.getenv("REPO_PATH", "/tmp/repo")

MAX_FILES = 40      # cap so large repos still render cleanly
MAX_EDGES = 80


def _relpath(filepath: str) -> str:
    """Turn an absolute cloned-repo path into a clean repo-relative path."""
    filepath = filepath.replace("\\", "/")
    repo = REPO_PATH.replace("\\", "/").rstrip("/")
    if filepath.startswith(repo + "/"):
        return filepath[len(repo) + 1:]
    # Fallback: keep the last few segments so it's still readable
    parts = filepath.split("/")
    return "/".join(parts[-3:])


def _node_id(relpath: str) -> str:
    """Deterministic, collision-free Mermaid node ID for a file path."""
    return "n_" + re.sub(r"[^a-zA-Z0-9]", "_", relpath).strip("_")


def _label(relpath: str) -> str:
    """Short display label: filename without extension."""
    name = relpath.split("/")[-1]
    name = re.sub(r"\.[a-zA-Z0-9]+$", "", name)  # strip any extension
    return name or "file"


def _group(relpath: str) -> str:
    """Directory used as the subgraph bucket — mirrors the real folder
    structure so the diagram doubles as an architecture map, e.g.
    'backend/app/agents'."""
    d = "/".join(relpath.split("/")[:-1])
    return d or "root"


def generate_file_diagram() -> str:
    """
    Generate a Mermaid graph LR diagram showing file-level architecture,
    grouped into subgraphs by directory. Each arrow represents at least
    one cross-file function call. Left-to-right layout spreads dense
    call graphs out far better than top-down for repos with heavy
    cross-file interconnection.
    """
    try:
        edges = _db.query(
            """
            MATCH (a:Function)-[:CALLS]->(b:Function)
            WHERE a.file IS NOT NULL
              AND b.file IS NOT NULL
              AND a.file <> b.file
            RETURN DISTINCT
              a.file AS src_file,
              b.file AS dst_file
            LIMIT $limit
            """,
            limit=MAX_EDGES,
        )
    except Exception as e:
        return f"graph LR\n  A[\"Graph unavailable: {str(e)[:40]}\"]"

    if not edges:
        return "graph LR\n  A[\"No cross-file calls found — analyze a repo first\"]"

    # Build file -> group + collect unique (src, dst) edges
    files: dict[str, str] = {}      # relpath -> group
    edge_pairs: set[tuple[str, str]] = set()

    for edge in edges:
        src_rel = _relpath(edge.get("src_file", ""))
        dst_rel = _relpath(edge.get("dst_file", ""))
        if not src_rel or not dst_rel or src_rel == dst_rel:
            continue
        files.setdefault(src_rel, _group(src_rel))
        files.setdefault(dst_rel, _group(dst_rel))
        edge_pairs.add((src_rel, dst_rel))

    if not files:
        return "graph LR\n  A[\"No cross-file relationships found\"]"

    truncated = False
    if len(files) > MAX_FILES:
        # Keep the files most connected — sort by degree, keep top MAX_FILES
        degree: dict[str, int] = {}
        for s, d in edge_pairs:
            degree[s] = degree.get(s, 0) + 1
            degree[d] = degree.get(d, 0) + 1
        kept = set(sorted(files, key=lambda f: -degree.get(f, 0))[:MAX_FILES])
        files = {f: g for f, g in files.items() if f in kept}
        edge_pairs = {(s, d) for s, d in edge_pairs if s in kept and d in kept}
        truncated = True

    # Group files by directory bucket
    groups: dict[str, list[str]] = {}
    for relpath, group in files.items():
        groups.setdefault(group, []).append(relpath)

    lines = ["graph LR"]
    lines.append("  classDef fileNode fill:#1a1d27,stroke:#1d9e75,stroke-width:1px,color:#e8e8ed;")

    for gi, (group, relpaths) in enumerate(sorted(groups.items())):
        sg_id = f"cluster_{gi}"
        sg_label = group.replace('"', "")
        lines.append(f'  subgraph {sg_id}["{sg_label}"]')
        for relpath in sorted(relpaths):
            lines.append(f'    {_node_id(relpath)}["{_label(relpath)}"]')
        lines.append("  end")

    for src, dst in sorted(edge_pairs):
        lines.append(f"  {_node_id(src)} --> {_node_id(dst)}")

    for relpath in files:
        lines.append(f"  class {_node_id(relpath)} fileNode;")

    if truncated:
        lines.append('  note["+ more files not shown (top connected files kept)"]')

    return "\n".join(lines)


def generate_class_diagram() -> str:
    """
    Generate a Mermaid classDiagram showing classes and their methods,
    across every language CodeScope parsed (not just Python).
    """
    try:
        classes = _db.query(
            """
            MATCH (c:Class)
            OPTIONAL MATCH (f:Function {cls: c.name})
            RETURN c.name AS cls, collect(DISTINCT f.name)[0..6] AS methods
            LIMIT 15
            """
        )
    except Exception:
        return "classDiagram\n  class NoData"

    if not classes:
        return "classDiagram\n  class NoClasses"

    lines = ["classDiagram"]
    seen_classes: set[str] = set()

    for row in classes:
        raw_name = row.get("cls") or "Unknown"
        cls = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name).strip("_") or "Unknown"
        if cls in seen_classes:
            continue
        seen_classes.add(cls)

        lines.append(f"  class {cls}")
        for method in (row.get("methods") or [])[:6]:
            if not method:
                continue
            m = re.sub(r"[^a-zA-Z0-9_]", "_", method)
            lines.append(f"  {cls} : +{m}()")

    if len(lines) == 1:
        return "classDiagram\n  class NoClasses"

    return "\n".join(lines)