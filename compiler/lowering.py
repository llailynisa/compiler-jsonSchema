from typing import Dict, List, Tuple

from compiler.ast_nodes import (JsonArray, JsonBool, JsonNode, JsonNull,
                                JsonNumber, JsonObject, JsonString)
from compiler.ir import ClassIR, EnumIR, FieldIR, IRNode, IRProgram
from compiler.semantic import collect_defs, ref_name

JAVA_RESERVED = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while",
    "true", "false", "null",
}

# tipe JSON Schema -> (tipe primitif / wajib, tipe wrapper / opsional)
SCALAR_TYPES = {
    "string": ("String", "String"),
    "integer": ("int", "Integer"),
    "number": ("double", "Double"),
    "boolean": ("boolean", "Boolean"),
}


# Penamaan

def safe_name(name: str) -> str:
    """Tambah '_' di belakang bila nama adalah reserved word Java."""
    return name + "_" if name in JAVA_RESERVED else name


def _words(text: str) -> List[str]:
    """Pecah teks menjadi kata; selain huruf/angka dianggap pemisah."""
    words: List[str] = []
    current = ""
    for ch in text:
        if ch.isalnum():
            current += ch
        elif current:
            words.append(current)
            current = ""
    if current:
        words.append(current)
    return words


def _fix_start(name: str) -> str:
    return "_" + name if name[0].isdigit() else name


def to_field_name(json_name: str) -> str:
    """is-aktif -> isAktif. Kosong -> 'field'. Reserved word -> 'class_'."""
    words = _words(json_name)
    if not words:
        return "field"
    first = words[0]
    first = first.lower() if first.isupper() else first[0].lower() + first[1:]
    rest = "".join(w[0].upper() + w[1:] for w in words[1:])
    return safe_name(_fix_start(first + rest))


def to_class_name(name: str) -> str:
    """jenis_simpanan -> JenisSimpanan. Kosong -> 'Unnamed'."""
    words = _words(name)
    if not words:
        return "Unnamed"
    return safe_name(_fix_start("".join(w[0].upper() + w[1:] for w in words)))


def to_enum_constant(value: str) -> str:
    """hari-raya -> HARI_RAYA. Kosong -> 'VALUE'."""
    words = _words(value)
    if not words:
        return "VALUE"
    return safe_name(_fix_start("_".join(w.upper() for w in words)))


# AST -> IR

def lower(ast: JsonNode) -> IRProgram:
    """Ubah AST skema yang sudah valid menjadi daftar ClassIR / EnumIR."""
    program: IRProgram = []
    if not isinstance(ast, JsonObject):
        return program

    defs = collect_defs(ast)

    if ast.get("type") is not None:
        name = to_class_name(ast.get_string("title") or "Schema")
        node = _lower_definition(name, ast, defs)
        if node is not None:
            program.append(node)

    defs_node = ast.get("$defs")
    if isinstance(defs_node, JsonObject):
        for m in defs_node.members:
            node = _lower_definition(to_class_name(m.key), m.value, defs)
            if node is not None:
                program.append(node)

    return program


def _is_enum(schema: JsonNode) -> bool:
    return (isinstance(schema, JsonObject)
            and schema.get_string("type") == "string"
            and isinstance(schema.get("enum"), JsonArray))


def _is_named_type(schema: JsonNode) -> bool:
    """True bila skema menghasilkan class atau enum sendiri."""
    return (isinstance(schema, JsonObject)
            and (schema.get_string("type") == "object" or _is_enum(schema)))


def _lower_definition(name: str, schema: JsonNode, defs: Dict[str, JsonNode]):
    """Skema object -> ClassIR, string+enum -> EnumIR, selain itu None (alias)."""
    if not isinstance(schema, JsonObject):
        return None
    tipe = schema.get_string("type")

    if tipe == "object":
        required = _required_names(schema)
        fields: List[FieldIR] = []
        props = schema.get("properties")
        if isinstance(props, JsonObject):
            for m in props.members:
                is_required = m.key in required
                java_type = _java_type(m.value, is_required, defs, ())
                fields.append(FieldIR(to_field_name(m.key), java_type,
                                      json_name=m.key, required=is_required))
        return ClassIR(name, fields)

    if _is_enum(schema):
        raw = [_literal_text(el) for el in schema.get("enum").elements]
        return EnumIR(name, [to_enum_constant(v) for v in raw], raw)

    return None


def _required_names(schema: JsonObject) -> set:
    required = schema.get("required")
    if not isinstance(required, JsonArray):
        return set()
    return {el.value for el in required.elements if isinstance(el, JsonString)}


def _literal_text(node: JsonNode) -> str:
    if isinstance(node, JsonString):
        return node.value
    if isinstance(node, JsonNumber):
        return node.lexeme
    if isinstance(node, JsonBool):
        return "true" if node.value else "false"
    if isinstance(node, JsonNull):
        return "null"
    return ""


def _java_type(schema: JsonNode, required: bool, defs: Dict[str, JsonNode],
               seen: Tuple[str, ...]) -> str:
    """Tipe Java final untuk satu skema. 'seen' mencegah alias melingkar."""
    if not isinstance(schema, JsonObject):
        return "Object"

    ref = schema.get("$ref")
    if isinstance(ref, JsonString):
        name = ref_name(ref.value)
        target = defs.get(name) if name else None
        if target is None or name in seen:
            return "Object"
        if _is_named_type(target):
            return to_class_name(name)
        return _java_type(target, required, defs, seen + (name,))

    tipe = schema.get_string("type")
    if tipe in SCALAR_TYPES:
        required_type, optional_type = SCALAR_TYPES[tipe]
        return required_type if required else optional_type
    if tipe == "array":
        items = schema.get("items")
        inner = _java_type(items, False, defs, seen) if items is not None else "Object"
        return f"List<{inner}>"
    return "Object"