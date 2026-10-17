"""
main.py - Antarmuka CLI compiler schema2java (JSON Schema -> class dan enum Java).

Alur:
    teks JSON -> Lexer -> Parser -> AST -> analyze -> lower -> IR -> generate_java

Contoh:
    python main.py examples/valid/01_anggota.json -o output/
    python main.py skema.json --dump-tokens
    python main.py skema.json --dump-ast
    python main.py skema.json --dump-ir

Kode keluar:
    0  berhasil
    1  input salah (lexical, syntax, atau semantic); tidak ada file .java dibuat
    2  file input tidak bisa dibaca
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from compiler.ast_nodes import dump as dump_ast
from compiler.codegen import generate_java
from compiler.error import LexerError, ParserError
from compiler.ir import check_ir, dump_ir
from compiler.lexer import Lexer
from compiler.lowering import lower
from compiler.parser import Parser
from compiler.semantic import analyze

EXIT_OK = 0
EXIT_COMPILE_ERROR = 1
EXIT_IO_ERROR = 2


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="schema2java",
        description="Compiler subset JSON Schema ke class dan enum Java.")
    p.add_argument("input", help="file JSON Schema (.json)")
    p.add_argument("-o", "--output", default="output",
                   help="folder keluaran file .java (default: output)")
    p.add_argument("--dump-tokens", action="store_true",
                   help="tampilkan token hasil lexer, lalu berhenti")
    p.add_argument("--dump-ast", action="store_true",
                   help="tampilkan AST hasil parser, lalu berhenti")
    p.add_argument("--dump-ir", action="store_true",
                   help="tampilkan IR hasil lowering, lalu berhenti")
    return p


def format_error(label: str, err: Exception) -> str:
    """Susun pesan error. Memakai code/line/column bila ada pada exception."""
    code = getattr(err, "code", None)
    line = getattr(err, "line", None)
    column = getattr(err, "column", None)
    message = getattr(err, "message", None) or str(err)
    if line is not None and column is not None:
        kode = f" {code}" if code else ""
        return f"{label}{kode} baris {line}, kolom {column}: {message}"
    return f"{label}: {message}"


def print_error(text: str) -> None:
    print(text, file=sys.stderr)


def dump_tokens(tokens) -> str:
    lines = []
    for tok in tokens:
        name = getattr(tok.type, "name", str(tok.type))
        lines.append(f"{tok.line}:{tok.column:<4} {name:<10} {tok.lexeme!r}")
    return "\n".join(lines)


def run(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    # 0. Baca file
    path = Path(args.input)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print_error(f"File tidak ditemukan: {path}")
        return EXIT_IO_ERROR
    except (OSError, UnicodeDecodeError) as e:
        print_error(f"File tidak bisa dibaca: {path} ({e})")
        return EXIT_IO_ERROR

    # 1. Lexer
    try:
        tokens = Lexer(text).tokenize()
    except LexerError as e:
        print_error(format_error("Error lexical", e))
        return EXIT_COMPILE_ERROR
    if args.dump_tokens:
        print(dump_tokens(tokens))
        return EXIT_OK

    # 2. Parser
    try:
        ast = Parser(tokens).parse()
    except ParserError as e:
        print_error(format_error("Error sintaks", e))
        return EXIT_COMPILE_ERROR
    if args.dump_ast:
        print(dump_ast(ast))
        return EXIT_OK

    # 3. Semantic analysis (mengembalikan daftar masalah, bukan exception)
    issues = analyze(ast)
    if issues:
        for issue in issues:
            print_error(str(issue))
        print_error(f"{len(issues)} error semantic. Tidak ada file Java yang dibuat.")
        return EXIT_COMPILE_ERROR

    # 4. Lowering AST -> IR
    program = lower(ast)
    problems = check_ir(program)
    if problems:
        for msg in problems:
            print_error(f"Error IR: {msg}")
        print_error(f"{len(problems)} error pada IR. Tidak ada file Java yang dibuat.")
        return EXIT_COMPILE_ERROR
    if args.dump_ir:
        print(dump_ir(program))
        return EXIT_OK

    # 5. Code generation
    written = generate_java(program, args.output)
    for f in written:
        print(f"Dibuat: {f}")
    print(f"Selesai: {len(written)} file Java di {args.output}")
    return EXIT_OK


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()