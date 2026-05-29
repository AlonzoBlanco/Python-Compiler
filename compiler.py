# =============================================================================
# compiler.py  —  Controlador Principal (Main driver)
#
# Uso:
#   python compiler.py <archivo_fuente>       # compilar + ejecutar
#   python compiler.py <archivo_fuente> --ir  # mostrar solo IR
#   python compiler.py <archivo_fuente> --asm # mostrar solo pseudoensamblador
#   python compiler.py <archivo_fuente> --all # mostrar todas las etapas
#   python compiler.py --test                 # ejecutar suite de pruebas integrada
# =============================================================================

import sys
import traceback

from lexer     import Lexer,    LexerError
from parser    import Parser,   ErrorSintactico
from semantic  import SemanticAnalyser, ErrorSemantico
from ir_gen    import IRGenerator, format_ir
from optimizer import optimize
from codegen   import generate_pseudoasm, format_asm, VM, VMError


# ─── Colores (desactivados en Windows si no hay soporte ANSI) ─────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _hdr(title: str):
    bar = "─" * 60
    print(f"\n{CYAN}{BOLD}{bar}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{bar}{RESET}")


# ─── Canal de Procesamiento (Pipeline) ────────────────────────────────────────

def compile_and_run(src: str, *,
                    show_tokens:   bool = False,
                    show_ast:      bool = False,
                    show_semantic: bool = False,
                    show_ir:       bool = False,
                    show_opt_ir:   bool = False,
                    show_asm:      bool = False,
                    run:           bool = True,
                    input_vals:    list = None) -> list[str]:
    """
    Pipeline completo. Retorna una lista con las cadenas de texto impresas.
    Lanza una excepción ante cualquier error de compilación.
    """

    # ── Etapa 1: Análisis Léxico ──────────────────────────────────────────────
    lexer  = Lexer(src)
    tokens = lexer.tokenize()
    if show_tokens:
        _hdr("Etapa 1 — Tokens")
        for t in tokens: print(" ", t)

    # ── Etapa 2: Análisis Sintáctico (Parsing) ────────────────────────────────
    parser = Parser(tokens)
    ast    = parser.parse()
    if show_ast:
        _hdr("Etapa 2 — AST")
        _print_ast(ast)

    # ── Etapa 3: Análisis Semántico ───────────────────────────────────────────
    analyser = SemanticAnalyser()
    analyser.analyse(ast)
    if show_semantic:
        _hdr("Etapa 3 — Tabla de Símbolos")
        print(analyser.format_results())

    # ── Etapa 4: Generación de IR ─────────────────────────────────────────────
    gen = IRGenerator()
    ir  = gen.generate(ast)
    if show_ir:
        _hdr("Etapa 4 — IR (antes de optimización)")
        print(format_ir(ir))

    # ── Etapa 5: Optimización ─────────────────────────────────────────────────
    opt_ir = optimize(ir)
    if show_opt_ir:
        _hdr("Etapa 5 — IR (después de optimización)")
        print(format_ir(opt_ir))

    # ── Etapa 6: Generación de código ─────────────────────────────────────────
    asm = generate_pseudoasm(opt_ir)
    if show_asm:
        _hdr("Etapa 6 — Pseudoensamblador")
        print(format_asm(asm))

    # ── Etapa 7: Ejecución en VM ──────────────────────────────────────────────
    output = []
    if run:
        if show_asm or show_ir or show_opt_ir or show_semantic:
            _hdr("Etapa 7 — Salida del Programa")
        vm = VM(asm, input_values=input_vals or [])
        output = vm.run()

    return output


# ─── Impresor simple de AST ───────────────────────────────────────────────────

def _print_ast(node, indent=0):
    prefix = "  " * indent
    name   = type(node).__name__
    from ast_nodes import (LiteralEntero, LiteralBooleano, Identificador,
                            OpBinaria, OpUnaria, LlamadaFuncion, DeclaracionFunc,
                            DeclaracionVar, Asignacion, Bloque, Programa)
    if isinstance(node, LiteralEntero):
        print(f"{prefix}LiteralEntero({node.value})")
    elif isinstance(node, LiteralBooleano):
        print(f"{prefix}LiteralBooleano({node.value})")
    elif isinstance(node, Identificador):
        print(f"{prefix}Identificador({node.name})")
    elif isinstance(node, OpBinaria):
        print(f"{prefix}OpBinaria({node.op})")
        _print_ast(node.left,  indent+1)
        _print_ast(node.right, indent+1)
    elif isinstance(node, OpUnaria):
        print(f"{prefix}OpUnaria({node.op})")
        _print_ast(node.operand, indent+1)
    elif isinstance(node, LlamadaFuncion):
        print(f"{prefix}LlamadaFuncion({node.name}, args={len(node.args)})")
        for a in node.args: _print_ast(a, indent+1)
    elif isinstance(node, DeclaracionFunc):
        params = ', '.join(f"{t} {n}" for t,n in node.params)
        print(f"{prefix}DeclaracionFunc {node.return_type} {node.name}({params})")
        _print_ast(node.body, indent+1)
    elif isinstance(node, DeclaracionVar):
        print(f"{prefix}DeclaracionVar {node.var_type} {node.name}")
        if node.init: _print_ast(node.init, indent+1)
    elif isinstance(node, Asignacion):
        print(f"{prefix}Asignacion({node.name})")
        _print_ast(node.value, indent+1)
    elif isinstance(node, Bloque):
        print(f"{prefix}Bloque")
        for s in node.stmts: _print_ast(s, indent+1)
    elif isinstance(node, Programa):
        print(f"{prefix}Programa")
        for d in node.declarations: _print_ast(d, indent+1)
    else:
        # Respaldo genérico
        print(f"{prefix}{name}")
        for field, val in vars(node).items():
            if isinstance(val, list):
                for item in val:
                    if hasattr(item, '__dataclass_fields__'): _print_ast(item, indent+1)
            elif hasattr(val, '__dataclass_fields__'):
                _print_ast(val, indent+1)


# ─── Pruebas integradas ───────────────────────────────────────────────

TESTS = [
    # (nombre, fuente, lineas_de_salida_esperadas, valores_de_entrada)
    (
        "Aritmética e impresión",
        """
        func int main() {
            int x = 10;
            int y = 3;
            int z = x * y + 2;
            print(z);
        }
        """,
        ["32"], []
    ),
    (
        "Condicional If-else",
        """
        func int main() {
            int a = 5;
            if (a > 3) {
                print(1);
            } else {
                print(0);
            }
        }
        """,
        ["1"], []
    ),
    (
        "Bucle While",
        """
        func int main() {
            int i = 0;
            while (i < 5) {
                i = i + 1;
            }
            print(i);
        }
        """,
        ["5"], []
    ),
    (
        "Bucle For",
        """
        func int main() {
            int sum = 0;
            for (int i = 1; i <= 4; i = i + 1) {
                sum = sum + i;
            }
            print(sum);
        }
        """,
        ["10"], []
    ),
    (
        "Bucle Do-while",
        """
        func int main() {
            int n = 1;
            do {
                n = n * 2;
            } while (n < 10);
            print(n);
        }
        """,
        ["16"], []
    ),
    (
        "Expresiones booleanas",
        """
        func int main() {
            bool a = true;
            bool b = false;
            bool c = a && !b;
            if (c || false) { print(1); }
            else            { print(0); }
        }
        """,
        ["1"], []
    ),
    (
        "Factorial recursivo",
        """
        func int fact(int n) {
            if (n <= 1) { return 1; }
            return n * fact(n - 1);
        }
        func int main() {
            print(fact(6));
        }
        """,
        ["720"], []
    ),
    (
        "Fibonacci recursivo",
        """
        func int fib(int n) {
            if (n <= 1) { return n; }
            return fib(n - 1) + fib(n - 2);
        }
        func int main() {
            print(fib(8));
        }
        """,
        ["21"], []
    ),
    (
        "Funciones anidadas y comentarios",
        """
        // Calcula n*(n+1)/2
        func int triangle(int n) {
            int s = 0;
            int i = 1;
            while (i <= n) {
                s = s + i;
                i = i + 1;
            }
            return s;
        }
        /* Punto de entrada principal */
        func int main() {
            print(triangle(5));   // debería ser 15
            print(triangle(10));  // debería ser 55
        }
        """,
        ["15", "55"], []
    ),
    (
        "Plegado de constantes (optimizador)",
        """
        func int main() {
            int x = 2 + 3 * 4;   // se pliega a 14
            print(x);
        }
        """,
        ["14"], []
    ),
]


def run_tests():
    passed = failed = 0
    print(f"\n{BOLD}Ejecutando {len(TESTS)} pruebas integradas…{RESET}\n")
    for name, src, expected, inp in TESTS:
        try:
            out = compile_and_run(src, run=True, input_vals=inp)
            if out == expected:
                print(f"  {GREEN}✓{RESET}  {name}")
                passed += 1
            else:
                print(f"  {RED}✗{RESET}  {name}")
                print(f"       Esperado : {expected}")
                print(f"       Obtenido : {out}")
                failed += 1
        except Exception as e:
            print(f"  {RED}✗{RESET}  {name}  — ERROR: {e}")
            failed += 1

    total = passed + failed
    colour = GREEN if failed == 0 else RED
    print(f"\n{colour}{BOLD}  {passed}/{total} pasaron{RESET}\n")
    return failed == 0


# ─── Punto de entrada CLI ─────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if '--test' in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    if not args or args[0].startswith('-'):
        print("Uso: python compiler.py <archivo> [--tokens] [--ast] [--semantic] [--ir] [--opt] [--asm] [--all]")
        print("     python compiler.py --test")
        sys.exit(1)

    fname = args[0]
    flags = set(args[1:])

    try:
        src = open(fname).read()
    except FileNotFoundError:
        print(f"{RED}Error: archivo no encontrado: {fname}{RESET}")
        sys.exit(1)

    show_all = '--all' in flags

    try:
        compile_and_run(
            src,
            show_tokens    = show_all or '--tokens'   in flags,
            show_ast       = show_all or '--ast'       in flags,
            show_semantic  = show_all or '--semantic'  in flags,
            show_ir        = show_all or '--ir'        in flags,
            show_opt_ir    = show_all or '--opt'       in flags,
            show_asm       = show_all or '--asm'       in flags,
            run            = True,
        )
    except (LexerError, ErrorSintactico, ErrorSemantico, VMError) as e:
        print(f"\n{RED}{BOLD}{e}{RESET}")
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()