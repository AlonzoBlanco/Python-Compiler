# =============================================================================
# parser.py  —  Etapa 2: Análisis Sintáctico
# Parser de descenso recursivo. Produce un AST a partir del flujo de tokens.
# =============================================================================

from lexer     import Token, TokenType
from ast_nodes import *


class ErrorSintactico(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0

    # ── Auxiliares ────────────────────────────────────────────────────────────

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _prev(self) -> Token:
        return self.tokens[self.pos - 1]

    def _check(self, *types) -> bool:
        return self._peek().type in types

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if t.type != TokenType.FIN_ARCHIVO:
            self.pos += 1
        return t

    def _expect(self, tt: TokenType, msg: str = "") -> Token:
        if self._peek().type == tt:
            return self._advance()
        raise ErrorSintactico(
            f"[Parser] Línea {self._peek().line}: "
            f"Se esperaba {tt.name}{(' — ' + msg) if msg else ''}, "
            f"se obtuvo {self._peek().type.name} ({self._peek().value!r})"
        )

    def _match(self, *types) -> bool:
        if self._check(*types):
            self._advance(); return True
        return False

    def _line(self) -> int:
        return self._peek().line

    def _is_type(self) -> bool:
        return self._check(TokenType.INT, TokenType.BOOL, TokenType.VOID)

    def _parse_type(self) -> str:
        if self._match(TokenType.INT):  return 'int'
        if self._match(TokenType.BOOL): return 'bool'
        if self._match(TokenType.VOID): return 'void'
        raise ErrorSintactico(f"[Parser] Línea {self._line()}: Se esperaba palabra clave de tipo")

    # ── Nivel superior (Top-level) ────────────────────────────────────────────

    def parse(self) -> Programa:
        decls = []
        while not self._check(TokenType.FIN_ARCHIVO):
            if self._check(TokenType.FUNC):
                decls.append(self._func_decl())
            elif self._is_type():
                decls.append(self._var_decl())
            else:
                raise ErrorSintactico(
                    f"[Parser] Línea {self._line()}: "
                    f"Se esperaba declaración de función o variable"
                )
        return Programa(declarations=decls, line=0)

    # ── Declaración de función ────────────────────────────────────────────────

    def _func_decl(self) -> DeclaracionFunc:
        line = self._line()
        self._expect(TokenType.FUNC)
        ret  = self._parse_type()
        name = self._expect(TokenType.IDENTIFICADOR, "nombre de la función").value
        self._expect(TokenType.PAR_IZQ)
        params = self._param_list()
        self._expect(TokenType.PAR_DER)
        body = self._block()
        return DeclaracionFunc(return_type=ret, name=name, params=params, body=body, line=line)

    def _param_list(self) -> list:
        params = []
        if self._is_type():
            params.append(self._single_param())
            while self._match(TokenType.COMA):
                params.append(self._single_param())
        return params

    def _single_param(self) -> tuple:
        ptype = self._parse_type()
        pname = self._expect(TokenType.IDENTIFICADOR, "nombre del parámetro").value
        return (ptype, pname)

    # ── Bloque ────────────────────────────────────────────────────────────────

    def _block(self) -> Bloque:
        line = self._line()
        self._expect(TokenType.LLAVE_IZQ)
        stmts = []
        while not self._check(TokenType.LLAVE_DER) and not self._check(TokenType.FIN_ARCHIVO):
            stmts.append(self._statement())
        self._expect(TokenType.LLAVE_DER)
        return Bloque(stmts=stmts, line=line)

    # ── Sentencias ────────────────────────────────────────────────────────────

    def _statement(self) -> Nodo:
        line = self._line()

        if self._is_type():
            return self._var_decl()

        if self._check(TokenType.IF):
            return self._if_stmt()

        if self._check(TokenType.WHILE):
            return self._while_stmt()

        if self._check(TokenType.DO):
            return self._do_while_stmt()

        if self._check(TokenType.FOR):
            return self._for_stmt()

        if self._check(TokenType.RETURN):
            return self._return_stmt()

        if self._check(TokenType.PRINT):
            return self._print_stmt()

        if self._check(TokenType.LLAVE_IZQ):
            return self._block()

        # asignación o declaración de expresión
        return self._expr_stmt()

    def _var_decl(self) -> DeclaracionVar:
        line  = self._line()
        vtype = self._parse_type()
        name  = self._expect(TokenType.IDENTIFICADOR, "nombre de la variable").value
        init  = None
        if self._match(TokenType.ASIGNACION):
            init = self._expr()
        self._expect(TokenType.PUNTO_Y_COMA)
        return DeclaracionVar(var_type=vtype, name=name, init=init, line=line)

    def _if_stmt(self) -> SentenciaIf:
        line = self._line()
        self._expect(TokenType.IF)
        self._expect(TokenType.PAR_IZQ)
        cond = self._expr()
        self._expect(TokenType.PAR_DER)
        then = self._block()
        else_ = None
        if self._match(TokenType.ELSE):
            else_ = self._block() if self._check(TokenType.LLAVE_IZQ) else self._if_stmt()
        return SentenciaIf(condition=cond, then_branch=then, else_branch=else_, line=line)

    def _while_stmt(self) -> SentenciaWhile:
        line = self._line()
        self._expect(TokenType.WHILE)
        self._expect(TokenType.PAR_IZQ)
        cond = self._expr()
        self._expect(TokenType.PAR_DER)
        return SentenciaWhile(condition=cond, body=self._block(), line=line)

    def _do_while_stmt(self) -> SentenciaDoWhile:
        line = self._line()
        self._expect(TokenType.DO)
        body = self._block()
        self._expect(TokenType.WHILE)
        self._expect(TokenType.PAR_IZQ)
        cond = self._expr()
        self._expect(TokenType.PAR_DER)
        self._expect(TokenType.PUNTO_Y_COMA)
        return SentenciaDoWhile(body=body, condition=cond, line=line)

    def _for_stmt(self) -> SentenciaFor:
        line = self._line()
        self._expect(TokenType.FOR)
        self._expect(TokenType.PAR_IZQ)

        # init: var_decl o asignación o vacío
        init = None
        if self._is_type():
            init = self._var_decl()          # consume ';'
        elif not self._check(TokenType.PUNTO_Y_COMA):
            init = self._assignment_or_expr()
            self._expect(TokenType.PUNTO_Y_COMA)
        else:
            self._advance()                  # consume ';'

        # condition
        cond = None
        if not self._check(TokenType.PUNTO_Y_COMA):
            cond = self._expr()
        self._expect(TokenType.PUNTO_Y_COMA)

        # update: asignación o vacío
        update = None
        if not self._check(TokenType.PAR_DER):
            update = self._assignment_or_expr()
        self._expect(TokenType.PAR_DER)

        body = self._block()
        return SentenciaFor(init=init, condition=cond, update=update, body=body, line=line)

    def _return_stmt(self) -> SentenciaReturn:
        line = self._line()
        self._expect(TokenType.RETURN)
        expr = None
        if not self._check(TokenType.PUNTO_Y_COMA):
            expr = self._expr()
        self._expect(TokenType.PUNTO_Y_COMA)
        return SentenciaReturn(expr=expr, line=line)

    def _print_stmt(self) -> SentenciaPrint:
        line = self._line()
        self._expect(TokenType.PRINT)
        self._expect(TokenType.PAR_IZQ)
        expr = self._expr()
        self._expect(TokenType.PAR_DER)
        self._expect(TokenType.PUNTO_Y_COMA)
        return SentenciaPrint(expr=expr, line=line)

    def _expr_stmt(self) -> Nodo:
        line = self._line()
        node = self._assignment_or_expr()
        self._expect(TokenType.PUNTO_Y_COMA)
        return node

    def _assignment_or_expr(self) -> Nodo:
        """Intenta parsear IDENTIFICADOR '=' expr; de lo contrario recurre a expr simple."""
        line = self._line()
        if (self._check(TokenType.IDENTIFICADOR) and
                self.pos + 1 < len(self.tokens) and
                self.tokens[self.pos + 1].type == TokenType.ASIGNACION):
            name = self._advance().value
            self._advance()          # consume '='
            val  = self._expr()
            return Asignacion(name=name, value=val, line=line)
        return SentenciaExpr(expr=self._expr(), line=line)

    # ── Expresiones ───────────────────────────────────────────────────────────

    def _expr(self) -> Nodo:
        return self._or_expr()

    def _or_expr(self) -> Nodo:
        left = self._and_expr()
        while self._check(TokenType.O_LOGICO):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._and_expr(), line=left.line)
        return left

    def _and_expr(self) -> Nodo:
        left = self._eq_expr()
        while self._check(TokenType.Y_LOGICO):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._eq_expr(), line=left.line)
        return left

    def _eq_expr(self) -> Nodo:
        left = self._rel_expr()
        while self._check(TokenType.IGUALDAD, TokenType.DESIGUALDAD):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._rel_expr(), line=left.line)
        return left

    def _rel_expr(self) -> Nodo:
        left = self._add_expr()
        while self._check(TokenType.MENOR_QUE, TokenType.MAYOR_QUE, TokenType.MENOR_IGUAL, TokenType.MAYOR_IGUAL):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._add_expr(), line=left.line)
        return left

    def _add_expr(self) -> Nodo:
        left = self._mul_expr()
        while self._check(TokenType.SUMA, TokenType.RESTA):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._mul_expr(), line=left.line)
        return left

    def _mul_expr(self) -> Nodo:
        left = self._unary()
        while self._check(TokenType.MULTIPLICACION, TokenType.DIVISION):
            op = self._advance().value
            left = OpBinaria(op=op, left=left, right=self._unary(), line=left.line)
        return left

    def _unary(self) -> Nodo:
        line = self._line()
        if self._check(TokenType.NEGACION):
            self._advance()
            return OpUnaria(op='!', operand=self._unary(), line=line)
        if self._check(TokenType.RESTA):
            self._advance()
            return OpUnaria(op='-', operand=self._unary(), line=line)
        return self._primary()

    def _primary(self) -> Nodo:
        line = self._line()
        tok  = self._peek()

        if tok.type == TokenType.LIT_ENTERO:
            self._advance()
            return LiteralEntero(value=tok.value, line=line)

        if tok.type == TokenType.TRUE:
            self._advance()
            return LiteralBooleano(value=True, line=line)

        if tok.type == TokenType.FALSE:
            self._advance()
            return LiteralBooleano(value=False, line=line)

        if tok.type == TokenType.READ:
            self._advance()
            self._expect(TokenType.PAR_IZQ)
            self._expect(TokenType.PAR_DER)
            return ExprLeer(line=line)

        if tok.type == TokenType.IDENTIFICADOR:
            self._advance()
            name = tok.value
            if self._check(TokenType.PAR_IZQ):
                self._advance()
                args = []
                if not self._check(TokenType.PAR_DER):
                    args.append(self._expr())
                    while self._match(TokenType.COMA):
                        args.append(self._expr())
                self._expect(TokenType.PAR_DER)
                return LlamadaFuncion(name=name, args=args, line=line)
            return Identificador(name=name, line=line)

        if tok.type == TokenType.PAR_IZQ:
            self._advance()
            expr = self._expr()
            self._expect(TokenType.PAR_DER)
            return expr

        raise ErrorSintactico(
            f"[Parser] Línea {line}: Token inesperado {tok.type.name} ({tok.value!r})"
        )