from typing import Any, List, Optional


class JsonNode:
    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column


class JsonString(JsonNode):
    def __init__(self, value: str, line: int, column: int):
        super().__init__(line, column)
        self.value = value


class JsonNumber(JsonNode):
    def __init__(self, value, lexeme: str, line: int, column: int):
        super().__init__(line, column)
        self.value = value      # int atau float
        self.lexeme = lexeme


class JsonBool(JsonNode):
    def __init__(self, value: bool, line: int, column: int):
        super().__init__(line, column)
        self.value = value


class JsonNull(JsonNode):
    def __init__(self, line: int, column: int):
        super().__init__(line, column)
        self.value = None


class JsonArray(JsonNode):
    def __init__(self, elements: List[JsonNode], line: int, column: int):
        super().__init__(line, column)
        self.elements = elements


class JsonMember:
    """Pasangan key-value di dalam JsonObject (menyimpan posisi key)."""

    def __init__(self, key: str, key_line: int, key_column: int, value: JsonNode):
        self.key = key
        self.key_line = key_line
        self.key_column = key_column
        self.value = value


class JsonObject(JsonNode):
    def __init__(self, members: List[JsonMember], line: int, column: int):
        super().__init__(line, column)
        self.members = members

    def get(self, key: str) -> Optional[JsonNode]:
        for m in self.members:
            if m.key == key:
                return m.value
        return None

    def get_string(self, key: str) -> Optional[str]:
        node = self.get(key)
        return node.value if isinstance(node, JsonString) else None

    def keys(self) -> List[str]:
        return [m.key for m in self.members]


# ------------------------------------------------------------------ Utilitas
def json_kind(node: JsonNode) -> str:
    """Nama jenis nilai JSON dari sebuah node."""
    if isinstance(node, JsonString):
        return "string"
    if isinstance(node, JsonNumber):
        return "number"
    if isinstance(node, JsonBool):
        return "boolean"
    if isinstance(node, JsonNull):
        return "null"
    if isinstance(node, JsonArray):
        return "array"
    if isinstance(node, JsonObject):
        return "object"
    return "unknown"


def dump(node: Any, indent: int = 0) -> str:
    """Cetak AST sebagai pohon teks (untuk --dump-ast)."""
    pad = "  " * indent
    pos = f"@{node.line}:{node.column}"
    if isinstance(node, JsonObject):
        lines = [f"{pad}JsonObject {pos}"]
        for m in node.members:
            lines.append(f"{pad}  Member {m.key!r} @{m.key_line}:{m.key_column}")
            lines.append(dump(m.value, indent + 2))
        return "\n".join(lines)
    if isinstance(node, JsonArray):
        lines = [f"{pad}JsonArray {pos}"]
        for el in node.elements:
            lines.append(dump(el, indent + 1))
        return "\n".join(lines)
    if isinstance(node, JsonString):
        return f"{pad}JsonString {node.value!r} {pos}"
    if isinstance(node, JsonNumber):
        return f"{pad}JsonNumber {node.lexeme} {pos}"
    if isinstance(node, JsonBool):
        return f"{pad}JsonBool {str(node.value).lower()} {pos}"
    if isinstance(node, JsonNull):
        return f"{pad}JsonNull {pos}"
    return f"{pad}{node!r}"