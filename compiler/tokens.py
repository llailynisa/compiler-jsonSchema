"""
tokens.py - Definisi Token dan daftar jenis token JSON.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TokenType(Enum):
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    COLON = ":"
    COMMA = ","
    STRING = "STRING"
    NUMBER = "NUMBER"
    TRUE = "true"
    FALSE = "false"
    NULL = "null"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str          # teks asli dari sumber
    line: int            # nomor baris (mulai 1)
    column: int          # nomor kolom (mulai 1)
    value: Any = None    # nilai Python (str / int / float / bool / None)

    def __str__(self) -> str:
        return f"{self.type.name}({self.lexeme!r}) @ {self.line}:{self.column}"


# Karakter tunggal -> jenis token
SYMBOLS = {
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ":": TokenType.COLON,
    ",": TokenType.COMMA,
}

# Literal kata kunci JSON -> (jenis token, nilai Python)
LITERALS = {
    "true": (TokenType.TRUE, True),
    "false": (TokenType.FALSE, False),
    "null": (TokenType.NULL, None),
}