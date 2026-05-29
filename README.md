# Python compiler for a C-like Mini-Language

Final compiler project developed in Python.  
This project implements a compiler for a small C-like programming language with typed functions, control structures, boolean expressions, intermediate code generation, optimization, and execution through a stack-based virtual machine.

## Features

- Primitive types: `int`, `bool`, and `void`
- Typed functions with parameters and return values
- Recursive function calls
- Control structures:
  - `if / else`
  - `while`
  - `do-while`
  - `for`
- Arithmetic, relational, and logical operators
- Basic input and output using `read()` and `print()`
- Line comments with `//`
- Block comments with `/* */`
- Lexical, syntactic, and semantic error handling
- Intermediate representation generation
- Basic IR optimization
- Pseudo-assembly generation
- Execution using a stack-based virtual machine

## Project Structure

```text
project/
├── compiler.py      # Main compiler controller
├── lexer.py         # Lexical analysis
├── parser.py        # Syntax analysis
├── ast_nodes.py     # AST node definitions
├── semantic.py      # Semantic analysis
├── ir_gen.py        # Intermediate code generation
├── optimizer.py     # IR optimization
├── codegen.py       # Pseudo-assembly and virtual machine
└── programa.txt     # Source file to compile
```

## Requirements

- Python 3.10 or higher
- No external dependencies required

## Usage

To compile and execute a source file:

```bash
python compiler.py programa.txt
```

To display specific compiler stages:

```bash
python compiler.py programa.txt --tokens
python compiler.py programa.txt --ast
python compiler.py programa.txt --ir
python compiler.py programa.txt --opt
python compiler.py programa.txt --asm
```

To display all compilation stages:

```bash
python compiler.py programa.txt --all
```

To run the integrated test suite:

```bash
python compiler.py --test
```

## Example Program

```c
func int fact(int n) {
    if (n <= 1) {
        return 1;
    }

    return n * fact(n - 1);
}

func int main() {
    print(fact(6));
}
```

Expected output:

```text
720
```

## Error Handling

The compiler reports errors depending on the compilation stage:

- `LexerError`: lexical errors
- `ParseError`: syntax errors
- `SemanticError`: type, scope, or declaration errors
- `VMError`: runtime errors in the virtual machine

## About

This project was created as a final assignment for a compiler design course.  
Its main goal is to demonstrate the complete compilation process, from lexical analysis to execution in a virtual machine.
```

## Suggested GitHub Repository Description

```text
Python compiler for a C-like mini-language with semantic analysis, IR generation, optimization, and a stack-based virtual machine.
```
