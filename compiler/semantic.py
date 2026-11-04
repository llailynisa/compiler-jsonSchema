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

    _check_java_names(ast, issues)

    return issues


def _check_java_names(ast: JsonObject, issues: List[SemanticIssue]) -> None:
    """Reject field identifiers that collide after Java name conversion."""
    from compiler.lowering import JAVA_RESERVED, to_class_name, to_field_name

    type_names = {}

    def register_type(name: str, node: JsonNode) -> None:
        converted = to_class_name(name)
        if converted in type_names:
            _add(issues, "E204", f"nama tipe '{name}' bentrok dengan '{type_names[converted]}' setelah konversi ke Java", node)
        else:
            type_names[converted] = name

    def visit_object(schema: JsonNode) -> None:
        if not isinstance(schema, JsonObject) or schema.get("$ref") is not None:
            return
        props = schema.get("properties")
        if isinstance(props, JsonObject):
            seen = {}
            for member in props.members:
                converted = to_field_name(member.key)
                if converted in seen:
                    _add(issues, "E204", f"nama property '{member.key}' bentrok dengan '{seen[converted]}' setelah konversi ke Java", member.value)
                if member.key in JAVA_RESERVED:
                    _add(issues, "E204", f"'{member.key}' adalah reserved word Java", member.value)
                seen.setdefault(converted, member.key)
                visit_object(member.value)
        items = schema.get("items")
        if items is not None:
            visit_object(items)

    if ast.get("type") is not None:
        register_type(ast.get_string("title") or "Schema", ast)

    def visit_inline_types(schema: JsonNode) -> None:
        if not isinstance(schema, JsonObject) or schema.get("$ref") is not None:
            return
        props = schema.get("properties")
        if isinstance(props, JsonObject):
            for member in props.members:
                child = member.value
                if isinstance(child, JsonObject) and child.get_string("type") == "object":
                    register_type(member.key, child)
                if isinstance(child, JsonObject) and child.get_string("type") == "array":
                    items = child.get("items")
                    if isinstance(items, JsonObject) and items.get_string("type") == "object":
                        register_type(member.key, items)
                visit_inline_types(child)
        items = schema.get("items")
        if items is not None:
            visit_inline_types(items)

    visit_object(ast)
    visit_inline_types(ast)
    defs = collect_defs(ast)
    for key, definition in defs.items():
        if isinstance(definition, JsonObject) and (definition.get_string("type") == "object" or
                (definition.get_string("type") == "string" and definition.get("enum") is not None)):
            register_type(key, definition)
        visit_object(definition)
        visit_inline_types(definition)


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
