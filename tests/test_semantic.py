"""Tes untuk compiler/semantic.py. Jalankan dari folder schema2java/:  python -m pytest

AST dibuat dengan to_ast(), yaitu jalan pintas yang mengubah dict/list Python
menjadi node AST. Parser tidak dipakai di sini. Setelah parser A jadi, tes
besar boleh diganti: Parser(Lexer(teks).tokenize()).parse()
"""

from compiler.ast_nodes import (JsonArray, JsonBool, JsonMember, JsonNull,
                                JsonNumber, JsonObject, JsonString)
from compiler.semantic import (SemanticIssue, analyze, collect_defs, ref_name)


def to_ast(x):
    if isinstance(x, dict):
        return JsonObject([JsonMember(k, 1, 1, to_ast(v)) for k, v in x.items()], 1, 1)
    if isinstance(x, list):
        return JsonArray([to_ast(i) for i in x], 1, 1)
    if isinstance(x, bool):
        return JsonBool(x, 1, 1)
    if isinstance(x, (int, float)):
        return JsonNumber(x, str(x), 1, 1)
    if x is None:
        return JsonNull(1, 1)
    return JsonString(x, 1, 1)


def codes(schema):
    return [i.code for i in analyze(to_ast(schema))]


ANGGOTA = {
    "title": "Anggota",
    "type": "object",
    "properties": {
        "id_anggota": {"type": "integer"},
        "nama": {"type": "string"},
        "is-aktif": {"type": "boolean"},
    },
    "required": ["nama", "id_anggota", "is-aktif"],
}

PINJAMAN = {
    "title": "Pinjaman",
    "type": "object",
    "properties": {
        "id_pinjaman": {"type": "integer"},
        "peminjam": {"$ref": "#/$defs/Anggota"},
        "status": {"$ref": "#/$defs/StatusPinjaman"},
        "angsuran": {"type": "array", "items": {"$ref": "#/$defs/Angsuran"}},
    },
    "required": ["id_pinjaman", "peminjam", "status"],
    "$defs": {
        "StatusPinjaman": {"type": "string", "enum": ["aktif", "lunas", "macet"]},
        "Anggota": {"type": "object",
                    "properties": {"nama": {"type": "string"}},
                    "required": ["nama"]},
        "Angsuran": {"type": "object",
                     "properties": {"ke": {"type": "integer"}},
                     "required": ["ke"]},
    },
}


# ---------- helper ----------

def test_ref_name():
    assert ref_name("#/$defs/Anggota") == "Anggota"
    assert ref_name("#/$defs/") is None
    assert ref_name("http://x.com/a.json") is None
    assert ref_name("#/definitions/Anggota") is None


def test_collect_defs():
    defs = collect_defs(to_ast(PINJAMAN))
    assert list(defs) == ["StatusPinjaman", "Anggota", "Angsuran"]
    assert collect_defs(to_ast(ANGGOTA)) == {}


def test_issue_str_memuat_kode_dan_posisi():
    s = str(SemanticIssue("E101", "contoh", 3, 7))
    assert "E101" in s and "baris 3" in s and "kolom 7" in s


# ---------- skema valid ----------

def test_skema_valid_tanpa_masalah():
    assert codes(ANGGOTA) == []
    assert codes(PINJAMAN) == []


def test_root_hanya_defs_valid():
    schema = {"$defs": {"Status": {"type": "string", "enum": ["a", "b"]}}}
    assert codes(schema) == []


# ---------- E100: bentuk dasar ----------

def test_e100_root_bukan_object():
    assert [i.code for i in analyze(to_ast(["x"]))] == ["E100"]


def test_e100_properties_bukan_object():
    assert codes({"type": "object", "properties": ["a"]}) == ["E100"]


def test_e100_required_bukan_array():
    assert codes({"type": "object", "properties": {}, "required": "a"}) == ["E100"]


def test_e100_ref_bukan_string():
    schema = {"type": "object", "properties": {"a": {"$ref": 5}}}
    assert codes(schema) == ["E100"]


def test_e100_defs_bukan_object():
    assert codes({"type": "object", "$defs": ["a"]}) == ["E100"]


def test_e100_enum_bukan_array():
    assert codes({"$defs": {"S": {"type": "string", "enum": "a"}}}) == ["E100"]


def test_e100_isi_required_bukan_string():
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": [5]}
    assert codes(schema) == ["E100"]


# ---------- E101: $ref ----------

def test_e101_ref_tidak_ditemukan():
    schema = {"type": "object",
              "properties": {"a": {"$ref": "#/$defs/Hilang"}},
              "$defs": {"Ada": {"type": "object"}}}
    assert codes(schema) == ["E101"]


def test_e101_ref_bukan_lokal():
    schema = {"type": "object", "properties": {"a": {"$ref": "http://x.com/s.json"}}}
    assert codes(schema) == ["E101"]


def test_e101_ref_di_dalam_array():
    schema = {"type": "object",
              "properties": {"a": {"type": "array", "items": {"$ref": "#/$defs/X"}}}}
    assert codes(schema) == ["E101"]


# ---------- E102: required ----------

def test_e102_required_tidak_ada_di_properties():
    schema = {"type": "object",
              "properties": {"nama": {"type": "string"}},
              "required": ["nama", "umur"]}
    issues = analyze(to_ast(schema))
    assert [i.code for i in issues] == ["E102"]
    assert "umur" in issues[0].message


def test_e102_di_dalam_defs():
    schema = {"$defs": {"A": {"type": "object",
                              "properties": {"x": {"type": "integer"}},
                              "required": ["y"]}}}
    assert codes(schema) == ["E102"]


# ---------- E103: type ----------

def test_e103_type_tidak_dikenal():
    schema = {"type": "object", "properties": {"a": {"type": "datetime"}}}
    issues = analyze(to_ast(schema))
    assert [i.code for i in issues] == ["E103"]
    assert "datetime" in issues[0].message


def test_e103_type_hilang():
    assert codes({"type": "object", "properties": {"a": {}}}) == ["E103"]


def test_e103_type_bukan_string():
    assert codes({"type": "object", "properties": {"a": {"type": 5}}}) == ["E103"]


def test_e103_null_tidak_didukung():
    assert codes({"type": "object", "properties": {"a": {"type": "null"}}}) == ["E103"]


def test_e103_di_dalam_defs():
    assert codes({"$defs": {"A": {"type": "foo"}}}) == ["E103"]


# ---------- E104: inline ----------

def test_e104_object_inline():
    schema = {"type": "object",
              "properties": {"alamat": {"type": "object", "properties": {}}}}
    assert codes(schema) == ["E104"]


def test_e104_object_inline_di_dalam_array():
    schema = {"type": "object",
              "properties": {"a": {"type": "array", "items": {"type": "object"}}}}
    assert codes(schema) == ["E104"]


def test_e104_enum_inline():
    schema = {"type": "object",
              "properties": {"s": {"type": "string", "enum": ["a"]}}}
    assert codes(schema) == ["E104"]


def test_enum_di_defs_boleh():
    schema = {"$defs": {"S": {"type": "string", "enum": ["a"]}}}
    assert codes(schema) == []


# ---------- E105: array ----------

def test_e105_array_tanpa_items():
    schema = {"type": "object", "properties": {"a": {"type": "array"}}}
    assert codes(schema) == ["E105"]


# ---------- perilaku umum ----------

def test_semua_masalah_dikumpulkan():
    schema = {
        "type": "object",
        "properties": {
            "a": {"$ref": "#/$defs/Hilang"},
            "b": {"type": "datetime"},
            "c": {"type": "array"},
        },
        "required": ["z"],
    }
    assert sorted(codes(schema)) == ["E101", "E102", "E103", "E105"]


def test_root_tanpa_type_dan_tanpa_defs():
    assert codes({"title": "X"}) == ["E103"]


def test_posisi_dibawa_dari_ast():
    ref = JsonString("#/$defs/Hilang", 7, 12)
    obj = JsonObject([JsonMember("$ref", 7, 5, ref)], 7, 3)
    root = JsonObject([
        JsonMember("type", 1, 1, JsonString("object", 1, 10)),
        JsonMember("properties", 2, 1, JsonObject([JsonMember("a", 7, 1, obj)], 6, 1)),
    ], 1, 1)
    issues = analyze(root)
    assert len(issues) == 1
    assert (issues[0].line, issues[0].column) == (7, 12)