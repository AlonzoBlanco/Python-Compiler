# =============================================================================
# optimizer.py  —  Etapa 5: Optimización Básica de IR
#
# Pases aplicados (en orden):
#   1. Propagación de Constantes — sustituye valores constantes conocidos en los operandos
#   2. Plegado de Constantes     — evalúa operaciones cuyos operandos son ambos constantes
#   3. Eliminación de Código Muerto — elimina asignaciones cuyo resultado nunca se lee
#
# El optimizador trabaja sobre la lista plana de instrucciones y retorna una nueva lista.
# =============================================================================

from ir_gen import Instruction


def _is_const(v) -> bool:
    """Verdadero si una cadena de valor representa una constante entera."""
    if v is None: return False
    try: int(str(v)); return True
    except ValueError: return False


def _as_int(v) -> int:
    return int(str(v))


# ── Pasos 1 & 2: Propagación + plegado de constantes ──────────────────────────

def _const_prop_fold(code: list[Instruction]) -> list[Instruction]:
    """
    Rastrea temporales / variables que contienen un valor constante.
    Sustituye y pliega donde sea posible.
    Se reinicia cuando una variable es reasignada.
    """
    env: dict[str, int] = {}   # nombre → valor constante
    result = []

    FOLDABLE = {'ADD','SUB','MUL','DIV','LT','GT','LEQ','GEQ','EQ','NEQ','AND','OR'}

    for instr in code:
        op, dest, arg1, arg2 = instr.op, instr.dest, instr.arg1, instr.arg2

        # ── Sustituir constantes conocidas en los argumentos ──────────────────
        # En una etiqueta o entrada de función no podemos saber qué camino llegó hasta aquí;
        # limpiamos de forma conservadora TODOS los valores rastreados para evitar un mal plegado en bucles.
        if op in ('LABEL', 'FUNC_BEGIN'):
            env.clear()

        if arg1 is not None and str(arg1) in env:
            arg1 = str(env[str(arg1)])
        if arg2 is not None and str(arg2) in env:
            arg2 = str(env[str(arg2)])

        # ── Intento de plegado ────────────────────────────────────────────────
        folded = False
        if op in FOLDABLE and _is_const(arg1) and _is_const(arg2):
            a, b = _as_int(arg1), _as_int(arg2)
            val = None
            if   op == 'ADD': val = a + b
            elif op == 'SUB': val = a - b
            elif op == 'MUL': val = a * b
            elif op == 'DIV' and b != 0: val = a // b
            elif op == 'LT':  val = int(a <  b)
            elif op == 'GT':  val = int(a >  b)
            elif op == 'LEQ': val = int(a <= b)
            elif op == 'GEQ': val = int(a >= b)
            elif op == 'EQ':  val = int(a == b)
            elif op == 'NEQ': val = int(a != b)
            elif op == 'AND': val = int(bool(a) and bool(b))
            elif op == 'OR':  val = int(bool(a) or  bool(b))
            if val is not None:
                env[dest] = val
                result.append(Instruction('ASSIGN', dest, str(val)))
                folded = True

        if not folded:
            if op == 'ASSIGN' and _is_const(arg1) and dest is not None:
                env[dest] = _as_int(arg1)
            elif op in ('NEG', 'NOT') and _is_const(arg1) and dest is not None:
                a = _as_int(arg1)
                val = -a if op == 'NEG' else int(not bool(a))
                env[dest] = val
                result.append(Instruction('ASSIGN', dest, str(val)))
                continue
            elif dest is not None and dest in env:
                # la variable se reasigna a un no-constante — desalojar
                del env[dest]

            result.append(Instruction(op, dest, arg1, arg2))

    return result


# ── Paso 3: Eliminación de código muerto ──────────────────────────────────────

def _dead_code(code: list[Instruction]) -> list[Instruction]:
    """
    Elimina instrucciones ASSIGN/aritméticas cuyo destino es un temporal
    que nunca es leído subsecuentemente por otra instrucción.
    Los temporales comienzan con 't' y un dígito.
    Las variables (definidas por el usuario) nunca se eliminan.
    """

    def _is_temp(name) -> bool:
        return name is not None and str(name).startswith('t') and str(name)[1:].isdigit()

    def _reads(instr: Instruction) -> set:
        used = set()
        for v in (instr.arg1, instr.arg2):
            if v is not None: used.add(str(v))
        return used

    # Reunir todos los temporales que alguna vez se leen
    read_temps: set[str] = set()
    for instr in code:
        read_temps |= _reads(instr)

    REMOVABLE = {'ASSIGN','ADD','SUB','MUL','DIV','NEG','NOT',
                 'LT','GT','LEQ','GEQ','EQ','NEQ','AND','OR'}

    result = []
    for instr in code:
        if (instr.op in REMOVABLE
                and _is_temp(instr.dest)
                and instr.dest not in read_temps):
            continue   # muerto — omitir
        result.append(instr)

    return result


# ── Paso 4: Eliminación de ramas constantes ───────────────────────────────────

def _const_branch(code: list[Instruction]) -> list[Instruction]:
    """
    Si IF_TRUE / IF_FALSE tiene una condición constante conocida,
    reemplazar con GOTO o eliminar.
    """
    result = []
    for instr in code:
        if instr.op == 'IF_TRUE' and _is_const(instr.arg1):
            if _as_int(instr.arg1):
                result.append(Instruction('GOTO', dest=instr.arg2))
            # de lo contrario: rama nunca tomada → descartar instrucción
        elif instr.op == 'IF_FALSE' and _is_const(instr.arg1):
            if not _as_int(instr.arg1):
                result.append(Instruction('GOTO', dest=instr.arg2))
        else:
            result.append(instr)
    return result


# ── Paso 5: Código inalcanzable después de GOTO incondicional ─────────────────

def _remove_unreachable(code: list[Instruction]) -> list[Instruction]:
    """Elimina instrucciones entre un GOTO incondicional y el siguiente LABEL."""
    result = []
    skipping = False
    for instr in code:
        if instr.op == 'LABEL':
            skipping = False
        if not skipping:
            result.append(instr)
        if instr.op == 'GOTO':
            skipping = True
    return result


# ── API Pública ───────────────────────────────────────────────────────────────

def optimize(code: list[Instruction]) -> list[Instruction]:
    """Ejecuta todos los pases de optimización y retorna el IR mejorado."""
    # Ejecutar propagación de constantes + plegado dos veces para que las constantes plegadas se propaguen más
    code = _const_prop_fold(code)
    code = _const_branch(code)
    code = _const_prop_fold(code)
    code = _const_branch(code)
    code = _remove_unreachable(code)
    code = _dead_code(code)
    return code