import shutil
import subprocess

import pytest

from compiler.codegen import (generate_class, generate_enum, generate_java,
                              generate_source)
from compiler.ir import ClassIR, EnumIR, FieldIR


# ---------- enum ----------

def test_enum_dasar():
    out = generate_enum(EnumIR("Status", ["ACTIVE", "IN_PROGRESS"]))
    assert out == (
        "public enum Status {\n"
        "    ACTIVE,\n"
        "    IN_PROGRESS\n"
        "}\n"
    )


def test_enum_satu_konstanta_tanpa_koma():
    out = generate_enum(EnumIR("One", ["A"]))
    assert "    A\n" in out
    assert "A," not in out


# ---------- class ----------

def test_class_dasar():
    node = ClassIR("User", [FieldIR("age", "int"), FieldIR("name", "String")])
    assert generate_class(node) == (
        "public class User {\n"
        "    private int age;\n"
        "    private String name;\n"
        "}\n"
    )


def test_class_tanpa_field():
    assert generate_class(ClassIR("Empty")) == "public class Empty {\n}\n"


def test_class_dengan_list_ada_import():
    node = ClassIR("User", [FieldIR("tags", "List<String>")])
    out = generate_class(node)
    assert out.startswith("import java.util.List;\n")
    assert "private List<String> tags;" in out


def test_class_tanpa_list_tanpa_import():
    out = generate_class(ClassIR("User", [FieldIR("age", "int")]))
    assert "import" not in out


def test_urutan_field_dipertahankan():
    node = ClassIR("U", [FieldIR("z", "int"), FieldIR("a", "int"), FieldIR("m", "int")])
    out = generate_class(node)
    assert out.index(" z;") < out.index(" a;") < out.index(" m;")


def test_referensi_ke_class_dan_enum_lain():
    node = ClassIR("Pinjaman", [
        FieldIR("peminjam", "Anggota"),
        FieldIR("status", "StatusPinjaman"),
        FieldIR("angsuran", "List<Angsuran>"),
    ])
    out = generate_class(node)
    assert "private Anggota peminjam;" in out
    assert "private StatusPinjaman status;" in out
    assert "private List<Angsuran> angsuran;" in out


# ---------- package ----------

def test_package_opsional():
    out = generate_class(ClassIR("User"), package="hasil")
    assert out.startswith("package hasil;\n\n")
    assert generate_enum(EnumIR("E", ["A"]), package="hasil").startswith("package hasil;")


def test_package_sebelum_import():
    node = ClassIR("User", [FieldIR("tags", "List<String>")])
    out = generate_class(node, package="hasil")
    assert out.index("package hasil;") < out.index("import java.util.List;")


# ---------- generate_source ----------

def test_generate_source_memilih_jenis_node():
    assert "public enum" in generate_source(EnumIR("E", ["A"]))
    assert "public class" in generate_source(ClassIR("C"))


def test_generate_source_node_asing():
    with pytest.raises(TypeError):
        generate_source("bukan node")


# ---------- generate_java (tulis file) ----------

def _program():
    return [
        EnumIR("Status", ["ACTIVE", "DONE"]),
        ClassIR("User", [FieldIR("name", "String"), FieldIR("status", "Status"),
                         FieldIR("tags", "List<String>")]),
    ]


def test_generate_java_satu_file_per_elemen(tmp_path):
    paths = generate_java(_program(), tmp_path)
    assert sorted(p.name for p in paths) == ["Status.java", "User.java"]
    assert all(p.exists() for p in paths)
    assert "public class User" in (tmp_path / "User.java").read_text(encoding="utf-8")


def test_generate_java_membuat_folder_output(tmp_path):
    target = tmp_path / "belum" / "ada"
    generate_java(_program(), target)
    assert (target / "User.java").exists()


def test_generate_java_program_kosong(tmp_path):
    assert generate_java([], tmp_path) == []


# ---------- javac ----------

@pytest.mark.skipif(shutil.which("javac") is None, reason="javac tidak terpasang")
def test_hasil_bisa_dikompilasi_javac(tmp_path):
    paths = generate_java(_program(), tmp_path)
    hasil = subprocess.run(["javac", *map(str, paths)], capture_output=True, text=True)
    assert hasil.returncode == 0, hasil.stderr