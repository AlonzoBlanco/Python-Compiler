# =============================================================================
# semantic.py  —  Etapa 3: Análisis Semántico y Tabla de Símbolos
#
# Responsabilidades:
#   • Construir una tabla de símbolos con ámbitos (variables + funciones)
#   • Comprobar tipos en todas las expresiones y sentencias
#   • Verificar que cada identificador sea declarado antes de su uso
#   • Verificar tipos de retorno dentro de las funciones
#   • Detectar declaraciones duplicadas dentro del mismo ámbito
# =============================================================================

from ast_nodes import *


class ErrorSemantico(Exception):
    pass


# ── Tabla de símbolos ─────────────────────────────────────────────────────────

class Symbol:
    def __init__(self, name: str, sym_type: str, kind: str = 'var',
                 params: list = None, return_type: str = None):
        self.name        = name
        self.sym_type    = sym_type      # 'int', 'bool', 'void'
        self.kind        = kind          # 'var' | 'func'
        self.params      = params or []  # lista de ('type', 'name') para funciones
        self.return_type = return_type


class Scope:
    def __init__(self, parent=None, func_return: str = None):
        self.table       = {}
        self.parent      = parent
        self.func_return = func_return   # propagado hacia adentro para comprobaciones de retorno

    def define(self, sym: Symbol, line: int):
        if sym.name in self.table:
            raise ErrorSemantico(
                f"[Semántico] Línea {line}: '{sym.name}' ya está declarada en este ámbito"
            )
        self.table[sym.name] = sym

    def lookup(self, name: str) -> Symbol | None:
        if name in self.table:
            return self.table[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def current_return_type(self) -> str | None:
        if self.func_return is not None:
            return self.func_return
        if self.parent:
            return self.parent.current_return_type()
        return None


# ── Analizador ────────────────────────────────────────────────────────────────

class SemanticAnalyser:
    def __init__(self):
        self.global_scope  = Scope()
        self.scope         = self.global_scope
        self._func_locals: dict[str, dict] = {}   # func_name → tabla de símbolos locales

    # ── Auxiliares de ámbito ──────────────────────────────────────────────────

    def _push(self, func_return: str = None):
        self.scope = Scope(parent=self.scope, func_return=func_return)

    def _pop(self):
        self.scope = self.scope.parent

    def _define(self, sym: Symbol, line: int):
        self.scope.define(sym, line)

    def _lookup(self, name: str, line: int) -> Symbol:
        sym = self.scope.lookup(name)
        if sym is None:
            raise ErrorSemantico(
                f"[Semántico] Línea {line}: Identificador indefinido '{name}'"
            )
        return sym

    def _error(self, line: int, msg: str):
        raise ErrorSemantico(f"[Semántico] Línea {line}: {msg}")

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def analyse(self, program: Programa):
        # Primera pasada: elevar todas las declaraciones de funciones para que funcione la recursión mutua
        for decl in program.declarations:
            if isinstance(decl, DeclaracionFunc):
                sym = Symbol(
                    name=decl.name,
                    sym_type=decl.return_type,
                    kind='func',
                    params=decl.params,
                    return_type=decl.return_type,
                )
                self._define(sym, decl.line)

        # Segunda pasada: análisis completo
        for decl in program.declarations:
            self._visit(decl)

    # ── Despacho (Dispatch) ───────────────────────────────────────────────────

    def _visit(self, node: Nodo) -> str:
        """Retorna la cadena de tipo de un nodo de expresión, o None para sentencias."""
        method = '_visit_' + type(node).__name__
        visitor = getattr(self, method, self._generic)
        return visitor(node)

    def _generic(self, node: Nodo):
        raise ErrorSemantico(f"[Semántico] Sin visitante para {type(node).__name__}")

    # ── Nivel superior (Top-level) ────────────────────────────────────────────

    def _visit_Programa(self, node: Programa):
        pass   # manejado en analyse()

    def _visit_DeclaracionFunc(self, node: DeclaracionFunc):
        self._push(func_return=node.return_type)
        for (ptype, pname) in node.params:
            self._define(Symbol(pname, ptype, 'var'), node.line)
        self._visit(node.body)
        self._func_locals[node.name] = dict(self.scope.table)   # capturar antes del pop
        self._pop()

    def _visit_DeclaracionVar(self, node: DeclaracionVar):
        if node.init is not None:
            init_type = self._visit(node.init)
            if init_type != node.var_type:
                self._error(node.line,
                    f"Incompatibilidad de tipos: no se puede asignar '{init_type}' a la variable '{node.name}' de tipo '{node.var_type}'"
                )
        self._define(Symbol(node.name, node.var_type, 'var'), node.line)

    # ── Sentencias ────────────────────────────────────────────────────────────

    def _visit_Bloque(self, node: Bloque):
        self._push()
        for stmt in node.stmts:
            self._visit(stmt)
        self._pop()

    def _visit_Asignacion(self, node: Asignacion):
        sym      = self._lookup(node.name, node.line)
        val_type = self._visit(node.value)
        if val_type != sym.sym_type:
            self._error(node.line,
                f"Incompatibilidad de tipos: no se puede asignar '{val_type}' a la variable '{node.name}' de tipo '{sym.sym_type}'"
            )

    def _visit_SentenciaIf(self, node: SentenciaIf):
        cond_type = self._visit(node.condition)
        if cond_type != 'bool':
            self._error(node.line, f"La condición del if debe ser bool, se obtuvo '{cond_type}'")
        self._visit(node.then_branch)
        if node.else_branch:
            self._visit(node.else_branch)

    def _visit_SentenciaWhile(self, node: SentenciaWhile):
        cond_type = self._visit(node.condition)
        if cond_type != 'bool':
            self._error(node.line, f"La condición del while debe ser bool, se obtuvo '{cond_type}'")
        self._visit(node.body)

    def _visit_SentenciaDoWhile(self, node: SentenciaDoWhile):
        self._visit(node.body)
        cond_type = self._visit(node.condition)
        if cond_type != 'bool':
            self._error(node.line, f"La condición del do-while debe ser bool, se obtuvo '{cond_type}'")

    def _visit_SentenciaFor(self, node: SentenciaFor):
        self._push()
        if node.init:    self._visit(node.init)
        if node.condition:
            ct = self._visit(node.condition)
            if ct != 'bool':
                self._error(node.line, f"La condición del for debe ser bool, se obtuvo '{ct}'")
        if node.update:  self._visit(node.update)
        # visitar sentencias del cuerpo directamente (body es un Bloque pero ya hicimos push de un ámbito)
        for stmt in node.body.stmts:
            self._visit(stmt)
        self._pop()

    def _visit_SentenciaReturn(self, node: SentenciaReturn):
        expected = self.scope.current_return_type()
        if expected is None:
            self._error(node.line, "return fuera de una función")
        if node.expr is None:
            if expected != 'void':
                self._error(node.line, f"La función debe retornar '{expected}', se obtuvo void")
        else:
            ret_type = self._visit(node.expr)
            if ret_type != expected:
                self._error(node.line,
                    f"Incompatibilidad de tipo de retorno: se esperaba '{expected}', se obtuvo '{ret_type}'"
                )

    def _visit_SentenciaPrint(self, node: SentenciaPrint):
        self._visit(node.expr)   # cualquier tipo es imprimible

    def _visit_SentenciaExpr(self, node: SentenciaExpr):
        self._visit(node.expr)

    # ── Expresiones ───────────────────────────────────────────────────────────

    def _visit_LiteralEntero(self, node: LiteralEntero) -> str:
        return 'int'

    def _visit_LiteralBooleano(self, node: LiteralBooleano) -> str:
        return 'bool'

    def _visit_ExprLeer(self, node: ExprLeer) -> str:
        return 'int'

    def _visit_Identificador(self, node: Identificador) -> str:
        sym = self._lookup(node.name, node.line)
        if sym.kind == 'func':
            self._error(node.line, f"'{node.name}' es una función, no una variable")
        return sym.sym_type

    def _visit_LlamadaFuncion(self, node: LlamadaFuncion) -> str:
        sym = self._lookup(node.name, node.line)
        if sym.kind != 'func':
            self._error(node.line, f"'{node.name}' no es una función")
        if len(node.args) != len(sym.params):
            self._error(node.line,
                f"'{node.name}' espera {len(sym.params)} argumentos, se obtuvieron {len(node.args)}"
            )
        for i, (arg, (ptype, pname)) in enumerate(zip(node.args, sym.params)):
            at = self._visit(arg)
            if at != ptype:
                self._error(node.line,
                    f"Argumento {i+1} de '{node.name}': se esperaba '{ptype}', se obtuvo '{at}'"
                )
        return sym.return_type

    def _visit_OpUnaria(self, node: OpUnaria) -> str:
        t = self._visit(node.operand)
        if node.op == '!':
            if t != 'bool':
                self._error(node.line, f"'!' requiere bool, se obtuvo '{t}'")
            return 'bool'
        if node.op == '-':
            if t != 'int':
                self._error(node.line, f"El '-' unario requiere int, se obtuvo '{t}'")
            return 'int'
        self._error(node.line, f"Operador unario desconocido '{node.op}'")

    # ── Formateador de resultados ─────────────────────────────────────────────

    def format_results(self) -> str:
        """Devuelve una representación legible de la tabla de símbolos completa."""
        SEP_W = "─" * 62
        SEP_N = "─" * 44
        lines = []

        # ── Ámbito global ─────────────────────────────────────────────────────
        lines.append(f"\n; ── Ámbito Global {SEP_W[18:]}")
        lines.append(f"  {'Nombre':<20} {'Categoría':<10} {'Tipo':<8}  Firma completa")
        lines.append(f"  {SEP_W}")
        for sym in self.global_scope.table.values():
            if sym.kind == 'func':
                params_str = ", ".join(f"{t} {n}" for t, n in sym.params) or "—"
                firma = f"{sym.return_type} {sym.name}({params_str})"
                lines.append(f"  {sym.name:<20} {'func':<10} {sym.return_type:<8}  {firma}")
            else:
                lines.append(f"  {sym.name:<20} {'var':<10} {sym.sym_type:<8}  (variable global)")

        # ── Ámbitos locales por función ───────────────────────────────────────
        for fname, table in self._func_locals.items():
            pad = SEP_N[len(fname) + 1:] if len(fname) + 1 < len(SEP_N) else ""
            lines.append(f"\n; ── Ámbito local: {fname} {pad}")
            lines.append(f"  {'Nombre':<20} {'Categoría':<10} Tipo")
            lines.append(f"  {SEP_N}")
            if not table:
                lines.append(f"  (sin variables locales)")
            for sym in table.values():
                cat = 'param' if sym.kind == 'var' else sym.kind
                lines.append(f"  {sym.name:<20} {cat:<10} {sym.sym_type}")

        lines.append("")
        return "\n".join(lines)

    ARITH_OPS   = {'+', '-', '*', '/'}
    LOGICAL_OPS = {'&&', '||'}
    REL_OPS     = {'<', '>', '<=', '>=', '==', '!='}

    def _visit_OpBinaria(self, node: OpBinaria) -> str:
        lt = self._visit(node.left)
        rt = self._visit(node.right)

        if node.op in self.ARITH_OPS:
            if lt != 'int' or rt != 'int':
                self._error(node.line,
                    f"El operador aritmético '{node.op}' requiere operandos int, se obtuvo '{lt}' y '{rt}'"
                )
            return 'int'

        if node.op in self.LOGICAL_OPS:
            if lt != 'bool' or rt != 'bool':
                self._error(node.line,
                    f"El operador lógico '{node.op}' requiere operandos bool, se obtuvo '{lt}' y '{rt}'"
                )
            return 'bool'

        if node.op in self.REL_OPS:
            if node.op in {'==', '!='}:
                if lt != rt:
                    self._error(node.line,
                        f"El operador de igualdad '{node.op}' requiere los mismos tipos, se obtuvo '{lt}' y '{rt}'"
                    )
            else:
                if lt != 'int' or rt != 'int':
                    self._error(node.line,
                        f"El operador relacional '{node.op}' requiere operandos int, se obtuvo '{lt}' y '{rt}'"
                    )
            return 'bool'

        self._error(node.line, f"Operador binario desconocido '{node.op}'")