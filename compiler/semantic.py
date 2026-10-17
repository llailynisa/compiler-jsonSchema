from dataclasses import dataclass
from typing import Dict, List, Optional

from compiler.ast_nodes import (JsonArray, JsonNode, JsonObject, JsonString)

VALID_TYPES = {"string", "integer", "number", "boolean", "object", "array"}
REF_PREFIX = "#/$defs/"


@dataclass
class SemanticIssue:
    """Satu masalah semantic beserta lokasinya."""

    code: str
    message: str
    line: int = 0
    column: int = 0

    def __str__(self) -> str:
        return f"Error {self.code} baris {self.line}, kolom {self.column}: {self.message}"


# Symbol table

def ref_name(ref: str) -> Optional[str]:
    """Ambil nama definisi dari '#/$defs/Nama'. None bila bukan $ref lokal."""
    if isinstance(ref, str) and ref.startswith(REF_PREFIX) and len(ref) > len(REF_PREFIX):
        return ref[len(REF_PREFIX):]
    return None


def collect_defs(ast: JsonNode) -> Dict[str, JsonNode]:
    """Symbol table: nama definisi di $defs -> node skemanya."""
    defs: Dict[str, JsonNode] = {}
    if isinstance(ast, JsonObject):
        node = ast.get("$defs")
        if isinstance(node, JsonObject):
            for m in node.members:
                defs[m.key] = m.value
    return defs


# Pengecekan

def analyze(ast: JsonNode) -> List[SemanticIssue]:
    """Periksa seluruh skema. Mengembalikan daftar masalah (kosong = valid)."""
    issues: List[SemanticIssue] = []

    if not isinstance(ast, JsonObject):
        _add(issues, "E100", "skema harus berupa object JSON", ast)
        return issues

    defs_node = ast.get("$defs")
    if defs_node is not None and not isinstance(defs_node, JsonObject):
        _add(issues, "E100", "$defs harus berupa object", defs_node)
    defs = collect_defs(ast)

    # Root dianggap skema bila punya "type", atau bila tidak punya $defs sama sekali.
    if ast.get("type") is not None or not defs:
        _check_schema(ast, defs, issues, top=True)

    if isinstance(defs_node, JsonObject):
        for m in defs_node.members:
            _check_schema(m.value, defs, issues, top=True)

    return issues


def _add(issues: List[SemanticIssue], code: str, message: str, node) -> None:
    issues.append(SemanticIssue(code, message,
                                getattr(node, "line", 0), getattr(node, "column", 0)))


def _check_schema(node: JsonNode, defs, issues, top: bool) -> None:
    """Periksa satu node skema. top=True untuk root dan isi $defs."""
    if not isinstance(node, JsonObject):
        _add(issues, "E100", "skema harus berupa object JSON", node)
        return

    ref = node.get("$ref")
    if ref is not None:
        _check_ref(ref, defs, issues)
        return

    type_node = node.get("type")
    if not isinstance(type_node, JsonString):
        _add(issues, "E103", "type hilang atau bukan string", node)
        return
    tipe = type_node.value
    if tipe not in VALID_TYPES:
        _add(issues, "E103", f"type '{tipe}' tidak dikenal", type_node)
        return

    enum_node = node.get("enum")
    if enum_node is not None and not isinstance(enum_node, JsonArray):
        _add(issues, "E100", "enum harus berupa array", enum_node)

    if tipe == "object":
        if not top:
            _add(issues, "E104",
                 "object inline tidak didukung, pindahkan ke $defs lalu pakai $ref", node)
            return
        _check_object(node, defs, issues)
    elif tipe == "array":
        items = node.get("items")
        if items is None:
            _add(issues, "E105", "array harus punya 'items'", node)
        else:
            _check_schema(items, defs, issues, top=False)
    elif enum_node is not None and not top:
        _add(issues, "E104",
             "enum inline tidak didukung, pindahkan ke $defs lalu pakai $ref", node)


def _check_object(node: JsonObject, defs, issues) -> None:
    props = node.get("properties")
    prop_keys: List[str] = []
    if props is not None:
        if not isinstance(props, JsonObject):
            _add(issues, "E100", "properties harus berupa object", props)
        else:
            prop_keys = props.keys()
            for m in props.members:
                _check_schema(m.value, defs, issues, top=False)

    required = node.get("required")
    if required is not None:
        if not isinstance(required, JsonArray):
            _add(issues, "E100", "required harus berupa array", required)
            return
        for el in required.elements:
            if not isinstance(el, JsonString):
                _add(issues, "E100", "isi required harus string", el)
            elif el.value not in prop_keys:
                _add(issues, "E102",
                     f"'{el.value}' ada di required tapi tidak ada di properties", el)


def _check_ref(ref: JsonNode, defs, issues) -> None:
    if not isinstance(ref, JsonString):
        _add(issues, "E100", "$ref harus berupa string", ref)
        return
    name = ref_name(ref.value)
    if name is None or name not in defs:
        _add(issues, "E101", f"$ref '{ref.value}' tidak ditemukan", ref)