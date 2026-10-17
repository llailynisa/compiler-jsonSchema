"""Tes end-to-end: file .json -> lexer -> parser -> semantic -> lowering -> codegen -> javac.
Jalankan dari folder schema2java/:  python -m pytest
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from compiler.codegen import generate_java
from compiler.errors import LexerError, ParserError
from compiler.lexer import Lexer
from compiler.lowering import lower
from compiler.parser import Parser
from compiler.semantic import analyze

ROOT = Path(__file__).resolve().parent.parent
VALID = sorted((ROOT / "examples" / "valid").glob("*.json"))
INVALID = ROOT / "examples" / "invalid"


def parse_file(path: Path):
    teks = path.read_text(encoding="utf-8")
    return Parser(Lexer(teks).tokenize()).parse()


# ---------- contoh valid: harus sampai .java dan lolos javac ----------

@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_lolos_semantic_dan_menghasilkan_java(path, tmp_path):
    ast = parse_file(path)
    assert analyze(ast) == []
    files = generate_java(lower(ast), tmp_path)
    assert files, "tidak ada file .java yang dihasilkan"


@pytest.mark.skipif(shutil.which("javac") is None, reason="javac tidak terpasang")
@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_bisa_dikompilasi_javac(path, tmp_path):
    files = generate_java(lower(parse_file(path)), tmp_path)
    hasil = subprocess.run(["javac", *map(str, files)], capture_output=True, text=True)
    assert hasil.returncode == 0, hasil.stderr


# ---------- contoh salah: tiap file harus gagal di tahap yang tepat ----------

def test_err_lexical_gagal_di_lexer():
    teks = (INVALID / "err_lexical.json").read_text(encoding="utf-8")
    with pytest.raises(LexerError):
        Lexer(teks).tokenize()


def test_err_syntax_gagal_di_parser():
    teks = (INVALID / "err_syntax.json").read_text(encoding="utf-8")
    tokens = Lexer(teks).tokenize()          # lexer harus lolos
    with pytest.raises(ParserError):
        Parser(tokens).parse()


def test_err_semantic_gagal_di_semantic():
    ast = parse_file(INVALID / "err_semantic.json")   # lexer dan parser harus lolos
    kode = [i.code for i in analyze(ast)]
    assert sorted(kode) == ["E101", "E102", "E103", "E104", "E105"]


# ---------- lewat CLI (bergantung pada main.py milik A) ----------

def test_cli_valid_menghasilkan_file_java(tmp_path):
    contoh = VALID[0]
    r = subprocess.run([sys.executable, str(ROOT / "main.py"), str(contoh), "-o", str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert list(tmp_path.glob("*.java"))


@pytest.mark.parametrize("nama", ["err_lexical.json", "err_syntax.json", "err_semantic.json"])
def test_cli_invalid_gagal_tanpa_traceback(nama, tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "main.py"), str(INVALID / nama), "-o", str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0
    assert "Traceback" not in r.stderr      # error ditampilkan rapi, bukan crash
    assert not list(tmp_path.glob("*.java"))  # tidak ada .java untuk input salah