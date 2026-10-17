"""
lexer.py - Fase 1: analisis leksikal (teks -> daftar token).

Ditulis manual (tanpa library json) mengikuti spesifikasi JSON (RFC 8259).
Melacak baris & kolom agar error menunjuk lokasi yang tepat.
"""

from typing import List

from .errors import (
    LEX_CONTROL_CHAR,
    LEX_INVALID_ESCAPE,
    LEX_INVALID_NUMBER,
    LEX_UNEXPECTED_CHAR,
    LEX_UNTERMINATED_STRING,
    LexerError,
)
from .tokens import LITERALS, SYMBOLS, Token, TokenType

WHITESPACE = frozenset(" \t\n\r")
DIGITS = frozenset("0123456789")
NONZERO_DIGITS = frozenset("123456789")
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
SIMPLE_ESCAPES = {
    '"': '"', "\\": "\\", "/": "/",
    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
}


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.pos = 0
        self.line = 1
        self.col = 1

    # ------------------------------------------------------- helper dasar
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.text[i] if i < self.n else ""

    def _advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self._peek() in WHITESPACE:  # "" (EOF) tidak ada di frozenset
            self._advance()

    # -------------------------------------------------------- API utama
    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while True:
            self._skip_whitespace()
            if self.pos >= self.n:
                tokens.append(Token(TokenType.EOF, "", self.line, self.col))
                return tokens
            tokens.append(self._next_token())

    def _next_token(self) -> Token:
        ch = self._peek()
        line, col = self.line, self.col

        if ch in SYMBOLS:
            self._advance()
            return Token(SYMBOLS[ch], ch, line, col)
        if ch == '"':
            return self._read_string()
        if ch == "-" or ch in DIGITS:
            return self._read_number()
        if ch.isascii() and ch.isalpha():
            return self._read_literal()

        hint = ""
        if ch == "'":
            hint = " (JSON hanya mengizinkan tanda kutip ganda \")"
        elif ch == "/":
            hint = " (komentar tidak didukung dalam JSON)"
        raise LexerError(LEX_UNEXPECTED_CHAR, f"Karakter tidak dikenal {ch!r}{hint}", line, col)

    # ------------------------------------------------------------ string
    def _read_string(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        self._advance()  # kutip pembuka
        chars: List[str] = []
        while True:
            if self.pos >= self.n:
                raise LexerError(LEX_UNTERMINATED_STRING,
                                 "String tidak ditutup (file berakhir)", line, col)
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            if ch in ("\n", "\r"):
                raise LexerError(LEX_UNTERMINATED_STRING,
                                 "String tidak ditutup sebelum akhir baris", line, col)
            if ord(ch) < 0x20:
                raise LexerError(LEX_CONTROL_CHAR,
                                 f"Karakter kontrol {ch!r} harus ditulis dengan escape",
                                 self.line, self.col)
            if ch == "\\":
                chars.append(self._read_escape())
                continue
            chars.append(self._advance())

        value = "".join(chars)
        try:  # gabungkan surrogate pair (\ud83d\ude00) menjadi satu karakter
            value = value.encode("utf-16", "surrogatepass").decode("utf-16")
        except UnicodeError:
            pass
        return Token(TokenType.STRING, self.text[start:self.pos], line, col, value)

    def _read_escape(self) -> str:
        eline, ecol = self.line, self.col
        self._advance()  # backslash
        esc = self._peek()
        if esc == "":
            raise LexerError(LEX_UNTERMINATED_STRING,
                             "String tidak ditutup (file berakhir)", eline, ecol)
        if esc in SIMPLE_ESCAPES:
            self._advance()
            return SIMPLE_ESCAPES[esc]
        if esc == "u":
            self._advance()
            digits = ""
            for _ in range(4):
                c = self._peek()
                if c == "" or c not in HEX_DIGITS:
                    raise LexerError(LEX_INVALID_ESCAPE,
                                     "Escape \\u harus diikuti 4 digit heksadesimal",
                                     eline, ecol)
                digits += self._advance()
            return chr(int(digits, 16))
        raise LexerError(LEX_INVALID_ESCAPE,
                         f"Escape sequence tidak valid: \\{esc}", eline, ecol)

    # ------------------------------------------------------------ angka
    def _read_number(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        is_float = False

        if self._peek() == "-":
            self._advance()
        if self._peek() == "0":
            self._advance()
            if self._peek() in DIGITS:
                raise LexerError(LEX_INVALID_NUMBER,
                                 "Angka tidak boleh diawali angka nol (mis. 01)", line, col)
        elif self._peek() in NONZERO_DIGITS:
            while self._peek() in DIGITS:
                self._advance()
        else:
            raise LexerError(LEX_INVALID_NUMBER,
                             "Digit diharapkan setelah tanda '-'", line, col)

        if self._peek() == ".":
            is_float = True
            self._advance()
            if self._peek() not in DIGITS:
                raise LexerError(LEX_INVALID_NUMBER,
                                 "Digit diharapkan setelah titik desimal", line, col)
            while self._peek() in DIGITS:
                self._advance()

        if self._peek() in ("e", "E"):
            is_float = True
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if self._peek() not in DIGITS:
                raise LexerError(LEX_INVALID_NUMBER,
                                 "Digit diharapkan pada bagian eksponen", line, col)
            while self._peek() in DIGITS:
                self._advance()

        lexeme = self.text[start:self.pos]
        value = float(lexeme) if is_float else int(lexeme)
        return Token(TokenType.NUMBER, lexeme, line, col, value)

    # ---------------------------------------------------------- literal
    def _read_literal(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        while self._peek().isascii() and self._peek().isalpha():
            self._advance()
        word = self.text[start:self.pos]
        if word in LITERALS:
            ttype, value = LITERALS[word]
            return Token(ttype, word, line, col, value)
        raise LexerError(LEX_UNEXPECTED_CHAR,
                         f"Literal tidak dikenal '{word}' (gunakan true, false, atau null "
                         f"dengan huruf kecil)", line, col)
