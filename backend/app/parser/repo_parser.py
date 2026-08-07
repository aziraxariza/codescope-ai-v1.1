"""
Repository parser using tree-sitter.
Clones a GitHub repo and extracts all functions, classes,
and call relationships into a list of structured dicts.

Multi-language: works on any repo, not just Python. Each supported
language declares which grammar to use, which node types count as
"function" / "class" definitions, and how to pull the callee name out
of a call expression. Unsupported files are skipped, not fatal.
"""

import os
import subprocess
import shutil
import stat
from typing import Any, Optional

from tree_sitter_languages import get_parser

# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------
# extensions        -> file suffixes routed to this language
# ts_lang           -> grammar name passed to tree_sitter_languages.get_parser
# function_types    -> node types treated as a function/method definition
# class_types       -> node types treated as a class/struct definition
# call_types        -> {node type: field name holding the callee expression}
# name_fallback     -> True if the node's name isn't in a "name" field and
#                       needs the C-style declarator dig (see _c_style_name)

LANGUAGES: dict[str, dict] = {
    "python": {
        "extensions": {".py"},
        "ts_lang": "python",
        "function_types": {"function_definition"},
        "class_types": {"class_definition"},
        "call_types": {"call": "function"},
    },
    "javascript": {
        "extensions": {".js", ".jsx", ".mjs", ".cjs"},
        "ts_lang": "javascript",
        "function_types": {"function_declaration", "method_definition"},
        "class_types": {"class_declaration"},
        "call_types": {"call_expression": "function"},
    },
    "typescript": {
        "extensions": {".ts"},
        "ts_lang": "typescript",
        "function_types": {"function_declaration", "method_definition"},
        "class_types": {"class_declaration"},
        "call_types": {"call_expression": "function"},
    },
    "tsx": {
        "extensions": {".tsx"},
        "ts_lang": "tsx",
        "function_types": {"function_declaration", "method_definition"},
        "class_types": {"class_declaration"},
        "call_types": {"call_expression": "function"},
    },
    "java": {
        "extensions": {".java"},
        "ts_lang": "java",
        "function_types": {"method_declaration", "constructor_declaration"},
        "class_types": {"class_declaration", "interface_declaration"},
        "call_types": {"method_invocation": "name"},
    },
    "go": {
        "extensions": {".go"},
        "ts_lang": "go",
        "function_types": {"function_declaration", "method_declaration"},
        "class_types": set(),  # Go has no classes
        "call_types": {"call_expression": "function"},
    },
    "rust": {
        "extensions": {".rs"},
        "ts_lang": "rust",
        "function_types": {"function_item"},
        "class_types": {"struct_item"},
        "call_types": {"call_expression": "function"},
    },
    "c": {
        "extensions": {".c", ".h"},
        "ts_lang": "c",
        "function_types": {"function_definition"},
        "class_types": set(),
        "call_types": {"call_expression": "function"},
        "name_fallback": True,
    },
    "cpp": {
        "extensions": {".cpp", ".cc", ".cxx", ".hpp", ".hh"},
        "ts_lang": "cpp",
        "function_types": {"function_definition"},
        "class_types": {"class_specifier", "struct_specifier"},
        "call_types": {"call_expression": "function"},
        "name_fallback": True,
    },
    "ruby": {
        "extensions": {".rb"},
        "ts_lang": "ruby",
        "function_types": {"method"},
        "class_types": {"class", "module"},
        "call_types": {"call": "method"},
    },
    "php": {
        "extensions": {".php"},
        "ts_lang": "php",
        "function_types": {"function_definition", "method_declaration"},
        "class_types": {"class_declaration"},
        "call_types": {
            "function_call_expression": "function",
            "member_call_expression": "name",
        },
    },
}

# extension -> language config, built once
_EXT_TO_LANG: dict[str, dict] = {
    ext: cfg for cfg in LANGUAGES.values() for ext in cfg["extensions"]
}

SKIP_DIRS = {
    "venv", ".venv", "__pycache__", ".git", "node_modules", "dist", "build",
    "target", ".next", "vendor", "bin", "obj", ".idea", ".vscode",
}

# Parsers are expensive to construct — cache one per language
_parser_cache: dict[str, Any] = {}


def _get_cached_parser(ts_lang: str):
    if ts_lang not in _parser_cache:
        _parser_cache[ts_lang] = get_parser(ts_lang)
    return _parser_cache[ts_lang]


def _remove_readonly(func, path, exc_info):
    """Handle read-only file deletion on Windows (used by .git internals)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repo(github_url: str, dest: str = "/tmp/repo") -> str:
    if os.path.exists(dest):
        shutil.rmtree(dest, onerror=_remove_readonly)
    result = subprocess.run(
        ["git", "clone", "--depth=1", github_url, dest],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")
    return dest


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------

def _c_style_name(node: Any) -> Optional[str]:
    """
    C/C++ function definitions don't expose a top-level "name" field —
    the identifier is buried inside a (possibly nested) declarator, e.g.
    function_definition -> function_declarator -> identifier, or with
    pointer/reference returns: function_definition -> pointer_declarator
    -> function_declarator -> identifier.
    """
    n = node.child_by_field_name("declarator")
    while n is not None:
        if n.type in ("identifier", "field_identifier"):
            return n.text.decode(errors="ignore")
        n = n.child_by_field_name("declarator")
    return None


def _get_def_name(node: Any, cfg: dict) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return name_node.text.decode(errors="ignore")
    if cfg.get("name_fallback"):
        name = _c_style_name(node)
        if name:
            return name
    return "unknown"


def _strip_qualifier(name: str) -> str:
    """
    Reduce a possibly-qualified callee expression to its final segment:
    "self.validate" -> "validate", "Type::method" -> "method",
    "obj->method" -> "method".
    """
    for sep in ("->", "::", "."):
        if sep in name:
            name = name.split(sep)[-1]
    return name.strip()


def extract_calls(node: Any, call_types: dict[str, str]) -> list[str]:
    """Walk a function AST node and collect deduplicated callee names."""
    calls: list[str] = []

    def find_calls(n: Any) -> None:
        field = call_types.get(n.type)
        if field:
            fn_node = n.child_by_field_name(field)
            if fn_node:
                name = _strip_qualifier(fn_node.text.decode(errors="ignore"))
                if name:
                    calls.append(name)
        for child in n.children:
            find_calls(child)

    find_calls(node)
    seen: set[str] = set()
    unique: list[str] = []
    for c in calls:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


# ---------------------------------------------------------------------------
# Per-file / per-repo parsing
# ---------------------------------------------------------------------------

def parse_file(filepath: str) -> list[dict]:
    """
    Parse a single source file with the appropriate language grammar.
    Returns a list of nodes:
      - {"type": "function", "name": ..., "file": ..., "class": ...,
         "calls": [...], "start_line": ..., "language": ...}
      - {"type": "class", "name": ..., "file": ..., "language": ...}
    Files whose extension isn't a supported language return [].
    """
    ext = os.path.splitext(filepath)[1].lower()
    cfg = _EXT_TO_LANG.get(ext)
    if cfg is None:
        return []

    parser = _get_cached_parser(cfg["ts_lang"])

    with open(filepath, "rb") as f:
        source = f.read()

    tree = parser.parse(source)
    results: list[dict] = []
    function_types = cfg["function_types"]
    class_types = cfg["class_types"]
    call_types = cfg["call_types"]
    language = cfg["ts_lang"]

    def walk(node: Any, parent_class: Optional[str] = None) -> None:
        if node.type in function_types:
            fn_name = _get_def_name(node, cfg)
            calls = extract_calls(node, call_types)

            results.append({
                "type": "function",
                "name": fn_name,
                "file": filepath,
                "class": parent_class or "",
                "calls": calls,
                "start_line": node.start_point[0] + 1,  # 1-indexed
                "language": language,
            })
            # Still descend, in case of nested functions/closures
            for child in node.children:
                walk(child, parent_class)
            return

        if node.type in class_types:
            cls_name = _get_def_name(node, cfg)

            if cls_name != "unknown":
                results.append({
                    "type": "class",
                    "name": cls_name,
                    "file": filepath,
                    "language": language,
                })

            for child in node.children:
                walk(child, parent_class=(cls_name if cls_name != "unknown" else parent_class))
            return  # don't re-walk children below

        for child in node.children:
            walk(child, parent_class)

    walk(tree.root_node)
    return results


def parse_repo(repo_path: str) -> list[dict]:
    """
    Walk every source file in a cloned repo whose extension matches a
    supported language, and return the combined list of function + class
    nodes. Works across a mixed-language repo, not just a single language.
    """
    all_nodes: list[dict] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in _EXT_TO_LANG:
                continue
            filepath = os.path.join(root, filename)
            try:
                nodes = parse_file(filepath)
                all_nodes.extend(nodes)
            except Exception:
                # Skip files that can't be parsed (encoding issues, syntax errors, etc.)
                pass

    return all_nodes


def detect_languages(repo_path: str) -> dict[str, int]:
    """Return a count of parsed files per language — used for the dashboard."""
    counts: dict[str, int] = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            cfg = _EXT_TO_LANG.get(ext)
            if cfg:
                counts[cfg["ts_lang"]] = counts.get(cfg["ts_lang"], 0) + 1
    return counts
