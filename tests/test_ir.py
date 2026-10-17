"""Tes untuk compiler/ir.py. Jalankan dari folder schema2java/:  python -m pytest"""

from dataclasses import fields, is_dataclass

from compiler.ir import (ClassIR, EnumIR, FieldIR, IRProgram, check_ir, dump_ir)


# ---------- struktur node ----------

def test_semua_node_adalah_dataclass():
    assert is_dataclass(FieldIR) and is_dataclass(EnumIR) and is_dataclass(ClassIR)


def test_nama_atribut_sesuai_kontrak():
    assert [f.name for f in fields(FieldIR)] == ["name", "java_type", "json_name", "required"]
    assert [f.name for f in fields(EnumIR)] == ["name", "constants", "json_values"]
    assert [f.name for f in fields(ClassIR)] == ["name", "fields"]


def test_kompatibel_mundur_dengan_pemakaian_sederhana():
    assert FieldIR("age", "Integer") == FieldIR(name="age", java_type="Integer")
    f = FieldIR("age", "Integer")
    assert f.json_name is None and f.required is False
    assert EnumIR("S", ["A"]).json_values == []


def test_default_list_tidak_dibagi_antar_objek():
    c1, c2 = ClassIR("A"), ClassIR("B")
    c1.fields.append(FieldIR("x", "int"))
    assert c2.fields == []
    e1, e2 = EnumIR("E1"), EnumIR("E2")
    e1.constants.append("ONE")
    e1.json_values.append("one")
    assert e2.constants == [] and e2.json_values == []


def test_kesetaraan():
    assert ClassIR("U", [FieldIR("a", "int")]) == ClassIR("U", [FieldIR("a", "int")])
    assert ClassIR("U") != ClassIR("V")


# ---------- method helper ----------

def test_is_list():
    assert FieldIR("tags", "List<String>").is_list()
    assert FieldIR("items", "List<Address>").is_list()
    assert not FieldIR("name", "String").is_list()


def test_is_primitive():
    assert FieldIR("age", "int").is_primitive()
    assert FieldIR("ok", "boolean").is_primitive()
    assert not FieldIR("age", "Integer").is_primitive()


def test_field_names_dan_uses_list():
    c = ClassIR("U", [FieldIR("name", "String"), FieldIR("tags", "List<String>")])
    assert c.field_names() == ["name", "tags"]
    assert c.uses_list()
    assert not ClassIR("V", [FieldIR("name", "String")]).uses_list()


# ---------- dump_ir ----------

def _contoh_program() -> IRProgram:
    return [
        EnumIR("Status", ["ACTIVE", "IN_PROGRESS"], ["active", "in-progress"]),
        ClassIR("User", [
            FieldIR("name", "String", "name", True),
            FieldIR("status", "Status", "status"),
            FieldIR("tags", "List<String>", "tags"),
        ]),
    ]


def test_dump_ir_berisi_informasi_penting():
    out = dump_ir(_contoh_program())
    assert "EnumIR Status" in out
    assert 'IN_PROGRESS   (json: "in-progress")' in out
    assert "ClassIR User" in out
    assert "- name: String [required]" in out
    assert "- tags: List<String>" in out


def test_dump_ir_program_kosong():
    assert dump_ir([]) == ""


# ---------- check_ir ----------

def test_check_ir_program_sehat():
    assert check_ir(_contoh_program()) == []


def test_check_ir_nama_ganda_dan_kosong():
    prog = [ClassIR("A"), ClassIR("A"), ClassIR("")]
    hasil = check_ir(prog)
    assert any("nama tipe ganda" in m for m in hasil)
    assert any("nama tipe tidak valid" in m for m in hasil)


def test_check_ir_field_ganda_dan_tipe_kosong():
    prog = [ClassIR("A", [FieldIR("x", "int"), FieldIR("x", ""), FieldIR("1bad", "int")])]
    hasil = check_ir(prog)
    assert any("nama field ganda" in m for m in hasil)
    assert any("java_type kosong" in m for m in hasil)
    assert any("nama field tidak valid" in m for m in hasil)


def test_check_ir_enum_bermasalah():
    prog = [EnumIR("E", ["A", "A", "B-C"], ["a"])]
    hasil = check_ir(prog)
    assert any("konstanta ganda" in m for m in hasil)
    assert any("konstanta tidak valid" in m for m in hasil)
    assert any("json_values" in m for m in hasil)


def test_check_ir_node_asing():
    assert any("node tidak dikenal" in m for m in check_ir(["bukan node"]))