# AGENTS.md

## Purpose

This project implements a **Bash / POSIX shell parser using Lark (LALR)** for static analysis (SAST).

The parser MUST produce a correct Lark parse tree and allow extraction of:

- commands
- arguments
- redirects
- assignments
- nested commands (subparses)

---

## 🔴 Hard Rules (STRICT)

### 1. DO NOT parse syntax in Python

You MUST NOT:

- manually parse strings
- use regex as a parser
- implement recursive descent in Python
- split commands by hand

👉 ALL syntax MUST be defined in `.lark` grammars.

---

### 2. Grammar-first approach ONLY

If something can be expressed in Lark grammar → it MUST be implemented in grammar.

Do NOT move grammar complexity into Python.

---

### 3. Sub-parsing must use Lark

For:

- `$()`
- backticks `` `...` ``
- `<(...)`, `>(...)`
- heredocs

You MUST:

1. Extract raw text
2. Re-parse using a separate Lark instance

❌ Do NOT parse nested structures with regex

---

### 4. Python is ONLY for

- calling Lark parsers
- Visitor / Transformer logic
- building SAST structures
- minimal preprocessing (e.g. heredoc isolation)

---

### 5. LALR ONLY

Always use:

```python
Lark(..., parser="lalr")
````

❌ Do NOT switch to Earley

---

### 6. DO NOT mix parsing and extraction

- Grammar → defines syntax
- Extractor → reads tree

❌ Extractor MUST NOT interpret syntax rules

---

## Required Workflow

For every change:

1. Modify `.lark` grammar
2. Add tests
3. Then update extractor if needed

---

## Forbidden Patterns

❌ Manual parsing:

```python
for char in text:
    ...
```

❌ Regex parsing:

```python
re.findall(r'\$\((.*?)\)', text)
```

❌ Syntax handling in extractor:

```python
if token == "if":
    ...
```

---

## Iteration Strategy

Implement features incrementally:

1. POSIX core ✅
2. Subparsers ✅
3. Arithmetic expansion `$(( ))`
4. Parameter expansion `${}`
5. Arrays
6. `[[ ... ]]`
7. Other Bash features

Each step MUST:

- pass tests
- not break existing grammar

---

## Core Principle

> If you are writing parsing logic in Python — you are doing it wrong.
