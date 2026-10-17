from pathlib import Path
from typing import List, Optional

from compiler.ir import ClassIR, EnumIR, FieldIR, IRNode, IRProgram

INDENT = "    "


def _package_line(package: Optional[str]) -> str:
    return f"package {package};\n\n" if package else ""


def _capitalize(name: str) -> str:
    """idAnggota -> IdAnggota (hanya huruf pertama yang diubah)."""
    return name[0].upper() + name[1:]


def _accessor_lines(f: FieldIR) -> List[str]:
    """Baris getter dan setter untuk satu field, diawali baris kosong."""
    cap = _capitalize(f.name)
    return [
        "",
        f"{INDENT}public {f.java_type} get{cap}() {{",
        f"{INDENT}{INDENT}return {f.name};",
        f"{INDENT}}}",
        "",
        f"{INDENT}public void set{cap}({f.java_type} {f.name}) {{",
        f"{INDENT}{INDENT}this.{f.name} = {f.name};",
        f"{INDENT}}}",
    ]


def generate_enum(node: EnumIR, package: Optional[str] = None) -> str:
    """Hasilkan teks Java untuk satu enum."""
    lines = [f"public enum {node.name} {{"]
    for i, const in enumerate(node.constants):
        sep = "," if i < len(node.constants) - 1 else ""
        lines.append(f"{INDENT}{const}{sep}")
    lines.append("}")
    return _package_line(package) + "\n".join(lines) + "\n"


def generate_class(node: ClassIR, package: Optional[str] = None,
                   accessors: bool = True) -> str:
    """Hasilkan teks Java untuk satu class (field private + getter/setter)."""
    header = _package_line(package)
    if node.uses_list():
        header += "import java.util.List;\n\n"

    lines = [f"public class {node.name} {{"]
    for f in node.fields:
        lines.append(f"{INDENT}private {f.java_type} {f.name};")
    if accessors:
        for f in node.fields:
            lines.extend(_accessor_lines(f))
    lines.append("}")
    return header + "\n".join(lines) + "\n"


def generate_source(node: IRNode, package: Optional[str] = None,
                    accessors: bool = True) -> str:
    """Pilih generator sesuai jenis node."""
    if isinstance(node, EnumIR):
        return generate_enum(node, package)
    if isinstance(node, ClassIR):
        return generate_class(node, package, accessors)
    raise TypeError(f"node IR tidak dikenal: {type(node).__name__}")


def generate_java(program: IRProgram, out_dir, package: Optional[str] = None,
                  accessors: bool = True) -> List[Path]:
    """
    Tulis satu file .java per elemen IR ke out_dir.
    Mengembalikan daftar path file yang ditulis.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for node in program:
        source = generate_source(node, package, accessors)
        path = out / f"{node.name}.java"
        path.write_text(source, encoding="utf-8")
        written.append(path)
    return written