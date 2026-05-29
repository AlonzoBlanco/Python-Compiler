# =============================================================================
# ir_gen.py  —  Etapa 4: Generación de Código Intermedio
#
# Produce una lista de objetos Instruction en forma de tres direcciones.
#
# Formato de instrucción:
#   op      dest    arg1    arg2
#  ─────────────────────────────────────────────
#  ASSIGN   x        v      -       x = v
#  ADD      t        a      b       t = a + b
#  SUB      t        a      b       t = a - b
#  MUL      t        a      b       t = a * b
#  DIV      t        a      b       t = a / b
#  NEG      t        a      -       t = -a
#  NOT      t        a      -       t = !a
#  LT / GT / LEQ / GEQ / EQ / NEQ   — comparación → bool temp
#  AND / OR  t       a      b
#  GOTO     label    -      -
#  IF_TRUE  -        cond   label   si cond goto label
#  IF_FALSE -        cond   label   si !cond goto label
#  LABEL    name     -      -
#  CALL     t        fname  nargs   t = fname(...)   (args empujados vía PARAM)
#  PARAM    -        v      -       empuja argumento
#  RETURN   -        v      -       retorna v (o None)
#  PRINT    -        v      -       imprime v
#  READ     t        -      -       t = read()
#  FUNC_BEGIN fname  -      -
#  FUNC_END  fname   -      -
# =============================================================================

from dataclasses import dataclass, field
from typing      import Optional, Any
from ast_nodes   import *


# ── Estructuras de datos del IR ───────────────────────────────────────────────

@dataclass
class Instruction:
    op:   str
    dest: Optional[str] = None
    arg1: Any           = None
    arg2: Any           = None

    def __repr__(self):
        parts = [self.op]
        if self.dest is not None: parts.append(str(self.dest))
        if self.arg1 is not None: parts.append(str(self.arg1))
        if self.arg2 is not None: parts.append(str(self.arg2))
        return "  " + "  ".join(parts)


def format_ir(instructions: list[Instruction]) -> str:
    """Imprime el listado del IR con formato legible."""
    lines = []
    for instr in instructions:
        op = instr.op
        if op == 'LABEL':
            lines.append(f"{instr.dest}:")
        elif op == 'FUNC_BEGIN':
            lines.append(f"\n; ── func {instr.dest} ────────────────────────────")
        elif op == 'FUNC_END':
            lines.append(f"; ── end {instr.dest}\n")
        elif op == 'ASSIGN':
            lines.append(f"    {instr.dest} = {instr.arg1}")
        elif op in ('ADD','SUB','MUL','DIV','AND','OR',
                    'LT','GT','LEQ','GEQ','EQ','NEQ'):
            lines.append(f"    {instr.dest} = {instr.arg1} {op} {instr.arg2}")
        elif op in ('NEG', 'NOT'):
            lines.append(f"    {instr.dest} = {op} {instr.arg1}")
        elif op == 'GOTO':
            lines.append(f"    goto {instr.dest}")
        elif op == 'IF_TRUE':
            lines.append(f"    if {instr.arg1} goto {instr.arg2}")
        elif op == 'IF_FALSE':
            lines.append(f"    ifFalse {instr.arg1} goto {instr.arg2}")
        elif op == 'CALL':
            lines.append(f"    {instr.dest} = call {instr.arg1} /{instr.arg2}")
        elif op == 'PARAM':
            lines.append(f"    param {instr.arg1}")
        elif op == 'RETURN':
            lines.append(f"    return {instr.arg1}" if instr.arg1 else "    return")
        elif op == 'PRINT':
            lines.append(f"    print {instr.arg1}")
        elif op == 'READ':
            lines.append(f"    {instr.dest} = read()")
        else:
            lines.append(f"    {op} {instr.dest} {instr.arg1} {instr.arg2}")
    return "\n".join(lines)


# ── Generador ─────────────────────────────────────────────────────────────────

class IRGenerator:
    def __init__(self):
        self.code:    list[Instruction] = []
        self._temp    = 0
        self._label   = 0

    # ── Auxiliares ────────────────────────────────────────────────────────────

    def _new_temp(self) -> str:
        self._temp += 1
        return f"t{self._temp}"

    def _new_label(self) -> str:
        self._label += 1
        return f"L{self._label}"

    def _emit(self, op, dest=None, arg1=None, arg2=None):
        self.code.append(Instruction(op, dest, arg1, arg2))

    # ── Entrada ──────────────────────────────────────────────────────

    def generate(self, program: Programa) -> list[Instruction]:
        for decl in program.declarations:
            self._visit(decl)
        return self.code

    # ── Dispatch ───────────────────────────────────────────────────

    def _visit(self, node: Nodo) -> Optional[str]:
        method = '_gen_' + type(node).__name__
        return getattr(self, method)(node)

    # ── Nivel superior (Top-level) ────────────────────────────────────────────

    def _gen_Programa(self, node: Programa):
        pass  # manejado en generate()

    def _gen_DeclaracionFunc(self, node: DeclaracionFunc):
        self._emit('FUNC_BEGIN', dest=node.name)
        # Saca los parámetros de la pila (empujados en orden → se sacan en reverso)
        for (ptype, pname) in reversed(node.params):
            self._emit('FUNC_PARAM', dest=pname)
        for stmt in node.body.stmts:
            self._visit(stmt)
        self._emit('FUNC_END', dest=node.name)

    # ── Sentencias ────────────────────────────────────────────────────────────

    def _gen_DeclaracionVar(self, node: DeclaracionVar):
        if node.init is not None:
            src = self._visit(node.init)
            self._emit('ASSIGN', dest=node.name, arg1=src)

    def _gen_Asignacion(self, node: Asignacion):
        src = self._visit(node.value)
        self._emit('ASSIGN', dest=node.name, arg1=src)

    def _gen_Bloque(self, node: Bloque):
        for stmt in node.stmts:
            self._visit(stmt)

    def _gen_SentenciaExpr(self, node: SentenciaExpr):
        self._visit(node.expr)

    def _gen_SentenciaPrint(self, node: SentenciaPrint):
        v = self._visit(node.expr)
        self._emit('PRINT', arg1=v)

    def _gen_SentenciaReturn(self, node: SentenciaReturn):
        if node.expr:
            v = self._visit(node.expr)
            self._emit('RETURN', arg1=v)
        else:
            self._emit('RETURN')

    # ── Flujo de control ──────────────────────────────────────────────────────

    def _gen_SentenciaIf(self, node: SentenciaIf):
        cond  = self._visit(node.condition)
        l_else = self._new_label()
        l_end  = self._new_label()

        self._emit('IF_FALSE', arg1=cond, arg2=l_else)
        self._visit(node.then_branch)
        if node.else_branch:
            self._emit('GOTO', dest=l_end)
        self._emit('LABEL', dest=l_else)
        if node.else_branch:
            self._visit(node.else_branch)
            self._emit('LABEL', dest=l_end)

    def _gen_SentenciaWhile(self, node: SentenciaWhile):
        l_check = self._new_label()
        l_end   = self._new_label()

        self._emit('LABEL', dest=l_check)
        cond = self._visit(node.condition)
        self._emit('IF_FALSE', arg1=cond, arg2=l_end)
        self._visit(node.body)
        self._emit('GOTO', dest=l_check)
        self._emit('LABEL', dest=l_end)

    def _gen_SentenciaDoWhile(self, node: SentenciaDoWhile):
        l_body = self._new_label()

        self._emit('LABEL', dest=l_body)
        self._visit(node.body)
        cond = self._visit(node.condition)
        self._emit('IF_TRUE', arg1=cond, arg2=l_body)

    def _gen_SentenciaFor(self, node: SentenciaFor):
        if node.init:
            self._visit(node.init)

        l_check = self._new_label()
        l_end   = self._new_label()

        self._emit('LABEL', dest=l_check)
        if node.condition:
            cond = self._visit(node.condition)
            self._emit('IF_FALSE', arg1=cond, arg2=l_end)

        self._visit(node.body)

        if node.update:
            self._visit(node.update)

        self._emit('GOTO', dest=l_check)
        self._emit('LABEL', dest=l_end)

    # ── Expresiones ───────────────────────────────────────────────────────────

    def _gen_LiteralEntero(self, node: LiteralEntero) -> str:
        return str(node.value)

    def _gen_LiteralBooleano(self, node: LiteralBooleano) -> str:
        return '1' if node.value else '0'

    def _gen_Identificador(self, node: Identificador) -> str:
        return node.name

    def _gen_ExprLeer(self, node: ExprLeer) -> str:
        t = self._new_temp()
        self._emit('READ', dest=t)
        return t

    def _gen_OpUnaria(self, node: OpUnaria) -> str:
        a = self._visit(node.operand)
        t = self._new_temp()
        self._emit('NEG' if node.op == '-' else 'NOT', dest=t, arg1=a)
        return t

    _OP_MAP = {
        '+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV',
        '&&': 'AND', '||': 'OR',
        '<': 'LT', '>': 'GT', '<=': 'LEQ', '>=': 'GEQ',
        '==': 'EQ', '!=': 'NEQ',
    }

    def _gen_OpBinaria(self, node: OpBinaria) -> str:
        # Evaluación de cortocircuito para && y ||
        if node.op == '&&':
            return self._short_circuit(node, is_and=True)
        if node.op == '||':
            return self._short_circuit(node, is_and=False)

        a = self._visit(node.left)
        b = self._visit(node.right)
        t = self._new_temp()
        self._emit(self._OP_MAP[node.op], dest=t, arg1=a, arg2=b)
        return t

    def _short_circuit(self, node: OpBinaria, is_and: bool) -> str:
        result  = self._new_temp()
        l_short = self._new_label()   # evaluación de omitir-el-segundo
        l_end   = self._new_label()

        left = self._visit(node.left)

        if is_and:
            # si left es falso, result = 0 inmediatamente
            self._emit('ASSIGN', dest=result, arg1=left)
            self._emit('IF_FALSE', arg1=left, arg2=l_short)
        else:
            # si left es verdadero, result = 1 inmediatamente
            self._emit('ASSIGN', dest=result, arg1=left)
            self._emit('IF_TRUE', arg1=left, arg2=l_short)

        right = self._visit(node.right)
        self._emit('ASSIGN', dest=result, arg1=right)
        self._emit('LABEL', dest=l_short)
        return result

    def _gen_LlamadaFuncion(self, node: LlamadaFuncion) -> str:
        for arg in node.args:
            v = self._visit(arg)
            self._emit('PARAM', arg1=v)
        t = self._new_temp()
        self._emit('CALL', dest=t, arg1=node.name, arg2=len(node.args))
        return t