# =============================================================================
# ast_nodes.py  —  Definiciones de los nodos del Árbol de Sintaxis Abstracta (AST)
# Cada construcción en el mini-lenguaje se mapea a una de estas dataclasses.
# =============================================================================

from dataclasses import dataclass, field
from typing import Optional, List, Any


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass
class Nodo:
    """Nodo base del AST. 'line' es solo por palabra clave (kw_only) para que
    los campos posicionales de las subclases (que no tienen valores por defecto)
    puedan aparecer antes sin generar un TypeError."""
    line: int = field(default=0, compare=False, kw_only=True)


# ── Expresiones ───────────────────────────────────────────────────────────────

@dataclass
class LiteralEntero(Nodo):
    value: int

@dataclass
class LiteralBooleano(Nodo):
    value: bool

@dataclass
class Identificador(Nodo):
    name: str

@dataclass
class OpBinaria(Nodo):
    op:    str   # +  -  * /  &&  ||  <  >  <=  >=  ==  !=
    left:  Nodo
    right: Nodo

@dataclass
class OpUnaria(Nodo):
    op:      str  # !  o - unario
    operand: Nodo

@dataclass
class LlamadaFuncion(Nodo):
    name: str
    args: List[Nodo]

@dataclass
class ExprLeer(Nodo):
    """función integrada read() — evalúa a un int leído desde stdin."""
    pass


# ── Sentencias (Statements) ───────────────────────────────────────────────────

@dataclass
class DeclaracionVar(Nodo):
    var_type: str   # 'int' | 'bool'
    name:     str
    init:     Optional[Nodo]   # expresión inicializadora opcional

@dataclass
class Asignacion(Nodo):
    name:  str
    value: Nodo

@dataclass
class SentenciaPrint(Nodo):
    expr: Nodo

@dataclass
class SentenciaReturn(Nodo):
    expr: Optional[Nodo]

@dataclass
class Bloque(Nodo):
    stmts: List[Nodo]

@dataclass
class SentenciaIf(Nodo):
    condition:   Nodo
    then_branch: Nodo            # siempre es un Bloque
    else_branch: Optional[Nodo]  # Bloque o None

@dataclass
class SentenciaWhile(Nodo):
    condition: Nodo
    body:      Nodo

@dataclass
class SentenciaDoWhile(Nodo):
    body:      Nodo
    condition: Nodo

@dataclass
class SentenciaFor(Nodo):
    init:      Optional[Nodo]   # DeclaracionVar o Asignacion o None
    condition: Optional[Nodo]
    update:    Optional[Nodo]   # Asignacion o None
    body:      Nodo

@dataclass
class SentenciaExpr(Nodo):
    """Una expresión simple utilizada como sentencia (ej. llamada a función)."""
    expr: Nodo


# ── Nivel superior (Top-level) ────────────────────────────────────────────────

@dataclass
class DeclaracionFunc(Nodo):
    return_type: str        # 'int' | 'bool' | 'void'
    name:        str
    params:      List[tuple]   # lista de ('type', 'name')
    body:        Bloque

@dataclass
class Programa(Nodo):
    declarations: List[Nodo]   # DeclaracionFunc o DeclaracionVar