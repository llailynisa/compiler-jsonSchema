from dataclasses import dataclass, field
from typing import List, Optional, Union

PRIMITIVE_TYPES = {"int", "double", "boolean"}

# Node IR

@dataclass
class FieldIR:
    """Satu field di dalam class Java."""

    name: str                          # nama field Java, mis. "age"
    java_type: str                     # tipe Java final, mis. "Integer"
    json_name: Optional[str] = None    # nama asli di JSON Schema, mis. "first-name"
    required: bool = False             # True bila masuk daftar "required"

    def is_list(self) -> bool:
        """True bila tipe field berupa List<...>."""
        return self.java_type.startswith("List<") and self.java_type.endswith(">")

    def is_primitive(self) -> bool:
        """True bila tipe field primitif Java (int, double, boolean)."""
        return self.java_type in PRIMITIVE_TYPES


@dataclass
class EnumIR:
    """Satu enum Java."""

    name: str                                                # mis. "Status"
    constants: List[str] = field(default_factory=list)       # mis. ["IN_PROGRESS"]
    json_values: List[str] = field(default_factory=list)     # mis. ["in-progress"]


@dataclass
class ClassIR:
    """Satu class Java beserta field-nya."""

    name: str                                                # mis. "User"
    fields: List[FieldIR] = field(default_factory=list)

    def field_names(self) -> List[str]:
        return [f.name for f in self.fields]

    def uses_list(self) -> bool:
        """True bila ada field List<...> (codegen perlu 'import java.util.List;')."""
        return any(f.is_list() for f in self.fields)


# Alias tipe (BUKAN node baru).
IRNode = Union[ClassIR, EnumIR]
IRProgram = List[IRNode]


# Helper: dump (untuk --dump-ir dan demo)

def dump_ir(program: IRProgram) -> str:
    """Ubah IR jadi teks yang mudah dibaca. Tidak mengubah IR."""
    lines: List[str] = []
    for node in program:
        if isinstance(node, EnumIR):
            lines.append(f"EnumIR {node.name}")
            for i, const in enumerate(node.constants):
                raw = node.json_values[i] if i < len(node.json_values) else None
                suffix = f'   (json: "{raw}")' if raw is not None else ""
                lines.append(f"  - {const}{suffix}")
        elif isinstance(node, ClassIR):
            lines.append(f"ClassIR {node.name}")
            for f in node.fields:
                flag = " [required]" if f.required else ""
                lines.append(f"  - {f.name}: {f.java_type}{flag}")
        else:
            lines.append(f"<node tidak dikenal: {type(node).__name__}>")
    return "\n".join(lines)

# Helper: pemeriksaan konsistensi IR

def check_ir(program: IRProgram) -> List[str]:
    problems: List[str] = []
    seen_types = set()

    for node in program:
        if not isinstance(node, (ClassIR, EnumIR)):
            problems.append(f"node tidak dikenal: {type(node).__name__}")
            continue

        if not _is_identifier(node.name):
            problems.append(f"nama tipe tidak valid: {node.name!r}")
        if node.name in seen_types:
            problems.append(f"nama tipe ganda: {node.name}")
        seen_types.add(node.name)

        if isinstance(node, EnumIR):
            if len(set(node.constants)) != len(node.constants):
                problems.append(f"konstanta ganda di enum {node.name}")
            for c in node.constants:
                if not _is_identifier(c):
                    problems.append(f"konstanta tidak valid di {node.name}: {c!r}")
            if node.json_values and len(node.json_values) != len(node.constants):
                problems.append(f"jumlah json_values != constants di enum {node.name}")
        else:
            names = node.field_names()
            if len(set(names)) != len(names):
                problems.append(f"nama field ganda di class {node.name}")
            for f in node.fields:
                if not _is_identifier(f.name):
                    problems.append(f"nama field tidak valid di {node.name}: {f.name!r}")
                if not f.java_type:
                    problems.append(f"java_type kosong di {node.name}.{f.name}")

    return problems


def _is_identifier(text: str) -> bool:
    return isinstance(text, str) and text.isidentifier()