# =============================================================================
# lexer.py  —  Etapa 1: Análisis Léxico
# Convierte el texto fuente en una lista plana de Tokens.
# Soporta: identificadores, literales enteros, ops aritméticos/lógicos/relacionales,
#          palabras clave, delimitadores, comentarios de línea //, comentarios de bloque /* */.
# =============================================================================

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # ── Literales ─────────────────────────────────────────────────────────────
    LIT_ENTERO = auto()
    # ── Palabras clave (Keywords del lenguaje, se mantienen igual) ────────────
    INT    = auto(); BOOL   = auto(); VOID   = auto()
    FUNC   = auto(); IF     = auto(); ELSE   = auto()
    WHILE  = auto(); DO     = auto(); FOR    = auto()
    RETURN = auto(); PRINT  = auto(); READ   = auto()
    TRUE   = auto(); FALSE  = auto()
    # ── Identificadores ───────────────────────────────────────────────────────
    IDENTIFICADOR = auto()
    # ── Aritméticos ───────────────────────────────────────────────────────────
    SUMA   = auto(); RESTA  = auto(); MULTIPLICACION = auto(); DIVISION = auto()
    # ── Lógicos ───────────────────────────────────────────────────────────────
    Y_LOGICO = auto(); O_LOGICO = auto(); NEGACION = auto()   # && || !
    # ── Relacionales ──────────────────────────────────────────────────────────
    MENOR_QUE = auto(); MAYOR_QUE = auto(); MENOR_IGUAL = auto()            # < > <=
    MAYOR_IGUAL = auto(); IGUALDAD = auto(); DESIGUALDAD = auto()           # >= == !=
    # ── Asignación ────────────────────────────────────────────────────────────
    ASIGNACION = auto()
    # ── Delimitadores ─────────────────────────────────────────────────────────
    PAR_IZQ = auto(); PAR_DER = auto()
    LLAVE_IZQ = auto(); LLAVE_DER = auto()
    PUNTO_Y_COMA = auto(); COMA = auto()
    # ── Especiales ────────────────────────────────────────────────────────────
    FIN_ARCHIVO = auto()


KEYWORDS = {
    'int': TokenType.INT,    'bool': TokenType.BOOL,  'void': TokenType.VOID,
    'func': TokenType.FUNC,  'if':   TokenType.IF,    'else': TokenType.ELSE,
    'while': TokenType.WHILE,'do':   TokenType.DO,    'for':  TokenType.FOR,
    'return': TokenType.RETURN, 'print': TokenType.PRINT, 'read': TokenType.READ,
    'true': TokenType.TRUE,  'false': TokenType.FALSE,
}


@dataclass
class Token:
    type:  TokenType
    value: object   # int, bool, str, o None
    line:  int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line})"


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, src: str):
        self.src  = src
        self.pos  = 0
        self.line = 1

    # ── Auxiliares ────────────────────────────────────────────────────────────

    def _error(self, msg: str):
        raise LexerError(f"[Lexer] Línea {self.line}: {msg}")

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else '\0'

    def _advance(self) -> str:
        ch = self.src[self.pos]; self.pos += 1
        if ch == '\n': self.line += 1
        return ch

    def _match(self, ch: str) -> bool:
        if self._peek() == ch:
            self._advance(); return True
        return False

    def _skip(self):
        """Omite espacios en blanco y comentarios."""
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in ' \t\r\n':
                self._advance()
            elif ch == '/' and self._peek(1) == '/':        # comentario //
                while self.pos < len(self.src) and self._peek() != '\n':
                    self._advance()
            elif ch == '/' and self._peek(1) == '*':        # comentario /* */
                self._advance(); self._advance()
                while self.pos < len(self.src):
                    if self._peek() == '*' and self._peek(1) == '/':
                        self._advance(); self._advance(); break
                    self._advance()
                else:
                    self._error("Comentario de bloque sin terminar")
            else:
                break

    # ── Punto de entrada principal ────────────────────────────────────────────

    def tokenize(self) -> list:
        tokens = []
        while True:
            self._skip()
            if self.pos >= len(self.src):
                tokens.append(Token(TokenType.FIN_ARCHIVO, None, self.line)); break

            line = self.line
            ch   = self._advance()

            # ── Literal entero ────────────────────────────────────────────────
            if ch.isdigit():
                num = ch
                while self._peek().isdigit(): num += self._advance()
                tokens.append(Token(TokenType.LIT_ENTERO, int(num), line))

            # ── Identificador o palabra clave ─────────────────────────────────
            elif ch.isalpha() or ch == '_':
                ident = ch
                while self._peek().isalnum() or self._peek() == '_':
                    ident += self._advance()
                tt = KEYWORDS.get(ident, TokenType.IDENTIFICADOR)
                if   tt == TokenType.TRUE:  val = True
                elif tt == TokenType.FALSE: val = False
                else:                       val = ident
                tokens.append(Token(tt, val, line))

            # ── Tokens de un solo carácter ────────────────────────────────────
            elif ch == '+': tokens.append(Token(TokenType.SUMA,   '+', line))
            elif ch == '-': tokens.append(Token(TokenType.RESTA,  '-', line))
            elif ch == '*': tokens.append(Token(TokenType.MULTIPLICACION,   '*', line))
            elif ch == '/': tokens.append(Token(TokenType.DIVISION,  '/', line))
            elif ch == '(': tokens.append(Token(TokenType.PAR_IZQ, '(', line))
            elif ch == ')': tokens.append(Token(TokenType.PAR_DER, ')', line))
            elif ch == '{': tokens.append(Token(TokenType.LLAVE_IZQ, '{', line))
            elif ch == '}': tokens.append(Token(TokenType.LLAVE_DER, '}', line))
            elif ch == ';': tokens.append(Token(TokenType.PUNTO_Y_COMA,   ';', line))
            elif ch == ',': tokens.append(Token(TokenType.COMA,  ',', line))

            # ── Tokens de dos caracteres ──────────────────────────────────────
            elif ch == '!':
                if self._match('='):
                    tokens.append(Token(TokenType.DESIGUALDAD, '!=', line))
                else:
                    tokens.append(Token(TokenType.NEGACION, '!', line))

            elif ch == '<':
                if self._match('='):
                    tokens.append(Token(TokenType.MENOR_IGUAL, '<=', line))
                else:
                    tokens.append(Token(TokenType.MENOR_QUE, '<', line))

            elif ch == '>':
                if self._match('='):
                    tokens.append(Token(TokenType.MAYOR_IGUAL, '>=', line))
                else:
                    tokens.append(Token(TokenType.MAYOR_QUE, '>', line))
            elif ch == '=':
                if self._match('='):
                    tokens.append(Token(TokenType.IGUALDAD, '==', line))
                else:
                    tokens.append(Token(TokenType.ASIGNACION, '=', line))
            elif ch == '&':
                if self._match('&'): tokens.append(Token(TokenType.Y_LOGICO, '&&', line))
                else: self._error("Se esperaba '&&'")
            elif ch == '|':
                if self._match('|'): tokens.append(Token(TokenType.O_LOGICO, '||', line))
                else: self._error("Se esperaba '||'")
            else:
                self._error(f"Carácter inesperado '{ch}'")

        return tokens