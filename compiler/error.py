"""
errors.py - Definisi error untuk semua fase compiler beserta kode error.

Hierarki:
    CompilerError
    ├── LexerError     (kode LEXxxx)  -> fase analisis leksikal
    ├── ParserError    (kode PARxxx)  -> fase analisis sintaks
    └── SemanticError  (kode SEMxxx)  -> fase analisis semantik
"""

from typing import Optional

# ---------------------------------------------------------------- Kode error
# Lexer
LEX_UNEXPECTED_CHAR = "LEX001"      # karakter tidak dikenal / literal tidak dikenal
LEX_UNTERMINATED_STRING = "LEX002"  # string tidak ditutup
LEX_INVALID_ESCAPE = "LEX003"       # escape sequence salah (\q, \u12)
LEX_INVALID_NUMBER = "LEX004"       # format angka salah (01, 1., -)
LEX_CONTROL_CHAR = "LEX005"         # karakter kontrol mentah di dalam string

# Parser
PAR_UNEXPECTED_TOKEN = "PAR001"     # token tak terduga saat mengharapkan nilai
PAR_EXPECTED_TOKEN = "PAR002"       # token yang diharapkan tidak ditemukan
PAR_TRAILING_CONTENT = "PAR003"     # ada konten setelah nilai JSON utama
PAR_DUPLICATE_KEY = "PAR004"        # key duplikat dalam satu object
PAR_TOO_DEEP = "PAR005"             # nesting terlalu dalam

# Semantic
SEM_UNKNOWN_TYPE = "SEM001"         # nilai type tidak dikenal
SEM_REQUIRED_NOT_FOUND = "SEM002"   # required merujuk property yang tidak ada
SEM_ARRAY_NO_ITEMS = "SEM003"       # array tanpa items
SEM_DUPLICATE_NAME = "SEM004"       # dua class/enum bernama sama
SEM_REF_NOT_FOUND = "SEM005"        # $ref ke definisi yang tidak ada
SEM_CIRCULAR_REF = "SEM006"         # referensi melingkar tanpa class perantara
SEM_ENUM_INVALID = "SEM007"         # enum kosong / campuran tipe
SEM_ENUM_UNSUPPORTED = "SEM008"     # enum non-string / nama konstanta tidak valid
SEM_INVALID_STRUCTURE = "SEM009"    # struktur / nilai keyword tidak valid
SEM_UNSUPPORTED_REF = "SEM010"      # $ref non-lokal (file/URL)
SEM_UNSUPPORTED_KEYWORD = "SEM011"  # oneOf/anyOf/allOf/not/patternProperties
SEM_MISSING_TYPE = "SEM012"         # skema tanpa type/enum/$ref
SEM_DUPLICATE_FIELD = "SEM013"      # dua property -> nama field Java sama

# Katalog (dipakai untuk dokumentasi & pengujian)
ERROR_CATALOG = {
    LEX_UNEXPECTED_CHAR: "Karakter atau literal tidak dikenal",
    LEX_UNTERMINATED_STRING: "String tidak ditutup",
    LEX_INVALID_ESCAPE: "Escape sequence dalam string tidak valid",
    LEX_INVALID_NUMBER: "Format angka tidak valid",
    LEX_CONTROL_CHAR: "Karakter kontrol mentah di dalam string",
    PAR_UNEXPECTED_TOKEN: "Token tak terduga (diharapkan nilai JSON)",
    PAR_EXPECTED_TOKEN: "Token yang diharapkan tidak ditemukan",
    PAR_TRAILING_CONTENT: "Ada konten setelah nilai JSON utama",
    PAR_DUPLICATE_KEY: "Key duplikat dalam satu object",
    PAR_TOO_DEEP: "Nesting JSON terlalu dalam",
    SEM_UNKNOWN_TYPE: "Nilai 'type' tidak dikenal",
    SEM_REQUIRED_NOT_FOUND: "'required' merujuk property yang tidak ada",
    SEM_ARRAY_NO_ITEMS: "Array tidak memiliki 'items'",
    SEM_DUPLICATE_NAME: "Nama class/enum bentrok",
    SEM_REF_NOT_FOUND: "'$ref' menunjuk definisi yang tidak ada",
    SEM_CIRCULAR_REF: "Referensi melingkar tanpa class perantara",
    SEM_ENUM_INVALID: "'enum' kosong atau bernilai campuran tipe",
    SEM_ENUM_UNSUPPORTED: "'enum' non-string / nama konstanta tidak valid",
    SEM_INVALID_STRUCTURE: "Struktur atau nilai keyword tidak valid",
    SEM_UNSUPPORTED_REF: "'$ref' non-lokal tidak didukung",
    SEM_UNSUPPORTED_KEYWORD: "Keyword di luar cakupan (oneOf/anyOf/allOf/not/...)",
    SEM_MISSING_TYPE: "Skema tidak memiliki 'type', 'enum', atau '$ref'",
    SEM_DUPLICATE_FIELD: "Dua property menghasilkan nama field Java yang sama",
}


# ------------------------------------------------------------ Kelas exception
class CompilerError(Exception):
    """Basis semua error compiler. Menyimpan kode, pesan, dan lokasi."""

    phase = "Compiler"

    def __init__(
        self,
        code: str,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        loc = ""
        if self.line is not None:
            loc = f" (baris {self.line}, kolom {self.column})"
        return f"[{self.code}] {self.phase} error{loc}: {self.message}"


class LexerError(CompilerError):
    phase = "Lexer"


class ParserError(CompilerError):
    phase = "Parser"


class SemanticError(CompilerError):
    phase = "Semantic"