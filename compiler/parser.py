"""
parser.py - Fase 2: analisis sintaks (token -> AST).

Recursive descent parser untuk tata bahasa JSON (lihat docs/grammar.md).
"""

from typing import List

from .ast_nodes import (
    JsonArray, JsonBool, JsonMember, JsonNode, JsonNull,
    JsonNumber, JsonObject, JsonString,
)
from .error import (
    PAR_DUPLICATE_KEY,
    PAR_EXPECTED_TOKEN,
    PAR_TOO_DEEP,
    PAR_TRAILING_CONTENT,
    PAR_UNEXPECTED_TOKEN,
    ParserError,
)
from .tokens import Token, TokenType

MAX_DEPTH = 100


def describe(tok: Token) -> str:
    if tok.type == TokenType.EOF:
        return "akhir file"
    return repr(tok.lexeme)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.depth = 0

    # ------------------------------------------------------- helper dasar
    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _expect(self, ttype: TokenType, what: str) -> Token:
        if self.cur.type != ttype:
            raise ParserError(PAR_EXPECTED_TOKEN,
                              f"Diharapkan {what}, ditemukan {describe(self.cur)}",
                              self.cur.line, self.cur.column)
        return self._advance()

    def _enter(self, tok: Token) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParserError(PAR_TOO_DEEP,
                              f"Nesting lebih dari {MAX_DEPTH} tingkat", tok.line, tok.column)

    def _leave(self) -> None:
        self.depth -= 1

    # -------------------------------------------------------- API utama
    def parse(self) -> JsonNode:
        node = self._parse_value()
        if self.cur.type != TokenType.EOF:
            raise ParserError(PAR_TRAILING_CONTENT,
                              f"Ada konten setelah nilai JSON utama: {describe(self.cur)}",
                              self.cur.line, self.cur.column)
        return node

    # -------------------------------------------------------- produksi
    def _parse_value(self) -> JsonNode:
        tok = self.cur
        t = tok.type
        if t == TokenType.LBRACE:
            return self._parse_object()
        if t == TokenType.LBRACKET:
            return self._parse_array()
        if t == TokenType.STRING:
            self._advance()
            return JsonString(tok.value, tok.line, tok.column)
        if t == TokenType.NUMBER:
            self._advance()
            return JsonNumber(tok.value, tok.lexeme, tok.line, tok.column)
        if t in (TokenType.TRUE, TokenType.FALSE):
            self._advance()
            return JsonBool(tok.value, tok.line, tok.column)
        if t == TokenType.NULL:
            self._advance()
            return JsonNull(tok.line, tok.column)
        if t == TokenType.EOF:
            raise ParserError(PAR_UNEXPECTED_TOKEN,
                              "Input berakhir, diharapkan sebuah nilai JSON",
                              tok.line, tok.column)
        raise ParserError(PAR_UNEXPECTED_TOKEN,
                          f"Token tak terduga {describe(tok)}, diharapkan nilai JSON",
                          tok.line, tok.column)

    def _parse_object(self) -> JsonObject:
        open_tok = self._advance()  # '{'
        self._enter(open_tok)
        members: List[JsonMember] = []
        seen = set()

        if self.cur.type == TokenType.RBRACE:
            self._advance()
            self._leave()
            return JsonObject(members, open_tok.line, open_tok.column)

        while True:
            if self.cur.type != TokenType.STRING:
                if self.cur.type == TokenType.RBRACE and members:
                    raise ParserError(PAR_EXPECTED_TOKEN,
                                      "Trailing comma tidak diperbolehkan di JSON "
                                      "(hapus koma sebelum '}')",
                                      self.cur.line, self.cur.column)
                raise ParserError(PAR_EXPECTED_TOKEN,
                                  f"Diharapkan key berupa string, ditemukan {describe(self.cur)}",
                                  self.cur.line, self.cur.column)
            key_tok = self._advance()
            if key_tok.value in seen:
                raise ParserError(PAR_DUPLICATE_KEY,
                                  f"Key duplikat {key_tok.value!r} dalam satu object",
                                  key_tok.line, key_tok.column)
            seen.add(key_tok.value)
            self._expect(TokenType.COLON, "':' setelah key")
            value = self._parse_value()
            members.append(JsonMember(key_tok.value, key_tok.line, key_tok.column, value))

            if self.cur.type == TokenType.COMMA:
                self._advance()
                continue
            if self.cur.type == TokenType.RBRACE:
                self._advance()
                break
            raise ParserError(PAR_EXPECTED_TOKEN,
                              f"Diharapkan ',' atau '}}', ditemukan {describe(self.cur)}",
                              self.cur.line, self.cur.column)

        self._leave()
        return JsonObject(members, open_tok.line, open_tok.column)

    def _parse_array(self) -> JsonArray:
        open_tok = self._advance()  # '['
        self._enter(open_tok)
        elements: List[JsonNode] = []

        if self.cur.type == TokenType.RBRACKET:
            self._advance()
            self._leave()
            return JsonArray(elements, open_tok.line, open_tok.column)

        while True:
            if self.cur.type == TokenType.RBRACKET and elements:
                raise ParserError(PAR_EXPECTED_TOKEN,
                                  "Trailing comma tidak diperbolehkan di JSON "
                                  "(hapus koma sebelum ']')",
                                  self.cur.line, self.cur.column)
            elements.append(self._parse_value())
            if self.cur.type == TokenType.COMMA:
                self._advance()
                continue
            if self.cur.type == TokenType.RBRACKET:
                self._advance()
                break
            raise ParserError(PAR_EXPECTED_TOKEN,
                              f"Diharapkan ',' atau ']', ditemukan {describe(self.cur)}",
                              self.cur.line, self.cur.column)

        self._leave()
        return JsonArray(elements, open_tok.line, open_tok.column)