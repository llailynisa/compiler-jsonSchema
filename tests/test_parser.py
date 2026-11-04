"""Tes untuk analisis sintaks JSON dan pembentukan AST."""

import pytest

from compiler.ast_nodes import (
    JsonArray, JsonBool, JsonNull, JsonNumber, JsonObject, JsonString,
)
from compiler.error import ParserError
from compiler.lexer import Lexer
from compiler.parser import Parser


def parse(text):
    return Parser(Lexer(text).tokenize()).parse()


def test_parse_object_dan_lookup_member():
    node = parse('{"nama": "Budi", "umur": 20}')

    assert isinstance(node, JsonObject)
    assert node.keys() == ["nama", "umur"]
    assert node.get_string("nama") == "Budi"
    assert node.get("umur").value == 20
    assert (node.line, node.column) == (1, 1)


def test_parse_array_dan_semua_tipe_nilai():
    node = parse('["teks", -2.5, true, false, null, [], {}]')

    assert isinstance(node, JsonArray)
    assert isinstance(node.elements[0], JsonString)
    assert node.elements[0].value == "teks"
    assert isinstance(node.elements[1], JsonNumber)
    assert (node.elements[1].value, node.elements[1].lexeme) == (-2.5, "-2.5")
    assert isinstance(node.elements[2], JsonBool) and node.elements[2].value is True
    assert isinstance(node.elements[3], JsonBool) and node.elements[3].value is False
    assert isinstance(node.elements[4], JsonNull) and node.elements[4].value is None
    assert isinstance(node.elements[5], JsonArray) and node.elements[5].elements == []
    assert isinstance(node.elements[6], JsonObject) and node.elements[6].members == []


def test_parse_nilai_akar_primitif():
    assert parse('"x"').value == "x"
    assert parse("42").value == 42
    assert parse("true").value is True
    assert isinstance(parse("null"), JsonNull)


def test_parse_object_dan_array_bersarang():
    node = parse('{"data": [{"id": 1}, [false]]}')
    data = node.get("data")

    assert isinstance(data, JsonArray)
    assert data.elements[0].get("id").value == 1
    assert data.elements[1].elements[0].value is False


@pytest.mark.parametrize("text", ["{}", "[]", "{\"x\": []}", "[1, {\"a\": true}]"])
def test_parse_koleksi_valid(text):
    assert parse(text) is not None


@pytest.mark.parametrize("text", [
    "", "{", "[", "{\"a\"}", "{\"a\":}", "{1: 2}",
    "[1,]", "{\"a\": 1,}", "{\"a\": 1", "[1 2]", "{\"a\": 1 \"b\": 2}",
])
def test_sintaks_tidak_valid_menghasilkan_parser_error(text):
    with pytest.raises(ParserError):
        parse(text)


def test_konten_setelah_nilai_akar_ditolak():
    with pytest.raises(ParserError) as caught:
        parse("{} []")

    assert caught.value.code == "PAR003"
    assert (caught.value.line, caught.value.column) == (1, 4)


def test_key_duplikat_ditolak_dan_lokasi_mengarah_ke_key_kedua():
    with pytest.raises(ParserError) as caught:
        parse('{"a": 1, "a": 2}')

    assert caught.value.code == "PAR004"
    assert (caught.value.line, caught.value.column) == (1, 10)


def test_key_duplikat_dalam_object_berbeda_diperbolehkan():
    node = parse('{"x": {"a": 1}, "y": {"a": 2}}')

    assert node.get("x").get("a").value == 1
    assert node.get("y").get("a").value == 2


def test_posisi_node_dan_key_dibawa_ke_ast():
    node = parse('{\n  "nama": 1\n}')
    member = node.members[0]

    assert (node.line, node.column) == (1, 1)
    assert (member.key_line, member.key_column) == (2, 3)
    assert (member.value.line, member.value.column) == (2, 11)


def test_nesting_melebihi_batas_ditolak():
    text = "[" * 101 + "0" + "]" * 101

    with pytest.raises(ParserError) as caught:
        parse(text)

    assert caught.value.code == "PAR005"
