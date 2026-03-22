# POSIX Shell Command Language: Parser Developer Summary

This document summarizes the critical specifications for developing a parser for the POSIX Shell Command Language (based on IEEE Std 1003.1-2017 / The Open Group Base Specifications Issue 7).

## 1. Lexical Analysis (Token Recognition)

The shell reads input in terms of lines. Tokenization occurs before parsing.

### 1.1 Token Recognition Rules

1. **Operators:** If the previous character was part of an operator and the current character extends it, it belongs to the operator token.
2. **Quotes:** If the current character is `\`, `'`, or `"` (unquoted), it affects quoting for subsequent characters. The token includes the quotes.
3. **Substitutions:** If the current character is unquoted `$` or `` ` ``, identify the start of parameter, command, or arithmetic expansion. Read sufficient input to determine the end (handling nesting). The token includes the expansion operators.
4. **Blanks:** An unquoted `<blank>` delimits the current token and is discarded.
5. **Comments:** A `#` (unquoted) discards itself and all subsequent characters up to the next `<newline>`.
6. **Words:** Any other character starts or appends to a word.

### 1.2 Quoting Mechanisms

Quoting removes special meaning from characters.

| Mechanism               | Syntax     | Behavior                                                                                                                                                                                                                                                                                                |
| :---------------------- | :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Escape**        | `\`      | Preserves literal value of the following character (except `<newline>`). `\` + `<newline>` is line continuation (removed entirely).                                                                                                                                                               |
| **Single-Quotes** | `'...'`  | Preserves literal value of**all** characters within. A single-quote cannot occur within single-quotes.                                                                                                                                                                                            |
| **Double-Quotes** | `"..."`  | Preserves literal value of all characters**except** `$`, `` ` ``, `\`, and `<newline>`. `<br>` - `$` introduces parameter/command/arithmetic expansion.`<br>` - `` ` `` introduces command substitution.`<br>` - `\` escapes only `$`, `` ` ``, `"`, `\`, or `<newline>`. |
| **Here-Document** | `<<word` | Redirects subsequent lines until a line containing only the delimiter.`<br>` - If `word` is quoted: No expansion on lines.`<br>` - If `word` is unquoted: Expand parameter, command, arithmetic expansions. `\` behaves like inside double-quotes.                                            |

### 1.3 Alias Substitution

* Occurs **after** tokenization, **before** grammar parsing.
* Applies only to the command name word of a simple command.
* Reserved words in correct grammatical context are **not** candidates for alias substitution.
* If an alias value ends in a `<blank>`, the next word is also checked for alias substitution.

## 2. Syntax & Grammar

### 2.1 Reserved Words

Recognized only when unquoted and in specific grammatical contexts (e.g., first word of a command).

| Reserved Words                                                     |
| :----------------------------------------------------------------- |
| `!` `{` `}` `case` `do` `done` `elif` `else`       |
| `esac` `fi` `for` `if` `in` `then` `until` `while` |

*Note: `[[`, `]]`, `function`, `select` are implementation-specific extensions.*

### 2.2 Formal Grammar (Simplified BNF)

The parser must adhere to the following structure (derived from Section 2.10.2).

```bnf
program          : linebreak complete_commands linebreak
complete_commands: complete_commands newline_list complete_command
                 | complete_command
complete_command : list separator_op | list
list             : list separator_op and_or | and_or
and_or           : pipeline | and_or AND_IF linebreak pipeline | and_or OR_IF linebreak pipeline
pipeline         : pipe_sequence | Bang pipe_sequence
pipe_sequence    : command | pipe_sequence '|' linebreak command
command          : simple_command | compound_command | compound_command redirect_list | function_definition
compound_command : brace_group | subshell | for_clause | case_clause | if_clause | while_clause | until_clause
subshell         : '(' compound_list ')'
compound_list    : linebreak term | linebreak term separator
term             : term separator and_or | and_or
for_clause       : For name do_group | For name sequential_sep do_group | For name linebreak in sequential_sep do_group | For name linebreak in wordlist sequential_sep do_group
case_clause      : Case WORD linebreak in linebreak case_list Esac
if_clause        : If compound_list Then compound_list else_part Fi
while_clause     : While compound_list do_group
until_clause     : Until compound_list do_group
function_definition : fname '(' ')' linebreak function_body
function_body    : compound_command | compound_command redirect_list
simple_command   : cmd_prefix cmd_word cmd_suffix | cmd_prefix cmd_word | cmd_prefix | cmd_name cmd_suffix | cmd_name
cmd_prefix       : io_redirect | cmd_prefix io_redirect | ASSIGNMENT_WORD | cmd_prefix ASSIGNMENT_WORD
cmd_suffix       : io_redirect | cmd_suffix io_redirect | WORD | cmd_suffix WORD
io_redirect      : io_file | IO_NUMBER io_file | io_here | IO_NUMBER io_here
io_file          : '<' filename | LESSAND filename | '>' filename | GREATAND filename | DGREAT filename | LESSGREAT filename | CLOBBER filename
io_here          : DLESS here_end | DLESSDASH here_end
```

### 2.3 Command Structures

1. **Simple Command:** Optional variable assignments and redirections, optionally followed by words (command name + arguments).
2. **Pipeline:** Sequence of commands separated by `|`. Optional `!` inverts exit status.
3. **List:** Sequence of pipelines separated by `;`, `&`, `&&`, or `||`.
   * `&`: Asynchronous execution (subshell).
   * `;`: Sequential execution.
   * `&&`: Execute next if previous succeeds (exit status 0).
   * `||`: Execute next if previous fails (exit status non-zero).
4. **Compound Commands:**
   * **Grouping:** `( list )` (subshell) or `{ list; }` (current environment).
   * **For Loop:** `for name [in word...] do list done`.
   * **Case:** `case word in pattern) list ;; ... esac`.
   * **If:** `if list then list [elif list then list] [else list] fi`.
   * **While/Until:** `while/until list do list done`.
5. **Function:** `fname() compound-command [io-redirect...]`.

## 3. Word Expansions

Expansions occur **after** parsing, before execution. The order is strict.

### 3.1 Order of Expansion

1. **Tilde Expansion:** `~user` -> home directory.
2. **Parameter Expansion:** `${parameter}`, `${parameter:-word}`, etc.
3. **Command Substitution:** `$(command)` or `` `command` ``.
4. **Arithmetic Expansion:** `$((expression))`.
5. **Field Splitting:** Based on `IFS` (unless quoted).
6. **Pathname Expansion:** Globbing (unless `set -f`).
7. **Quote Removal:** Removing quoting characters from the result.

### 3.2 Parameter Expansion Syntax

Format: `${expression}`

* **Basic:** `${parameter}`
* **Modifiers:**
  * `${parameter:-word}` (Use Default)
  * `${parameter:=word}` (Assign Default)
  * `${parameter:?word}` (Error if Null/Unset)
  * `${parameter:+word}` (Use Alternative)
  * `${#parameter}` (String Length)
  * `${parameter%word}` (Remove Smallest Suffix Pattern)
  * `${parameter%%word}` (Remove Largest Suffix Pattern)
  * `${parameter#word}` (Remove Smallest Prefix Pattern)
  * `${parameter##word}` (Remove Largest Prefix Pattern)

### 3.3 Command Substitution

* `$(command)`: Preferred form. Nesting allowed.
* `` `command` ``: Legacy form. Backslashes retain literal meaning except before `$`, `` ` ``, `\`, or `<newline>`.
* **Note:** `$((` starts Arithmetic Expansion. If ambiguous, Arithmetic takes precedence. To force command substitution with subshell, use `$ ( (command) )` (space required).

### 3.4 Arithmetic Expansion

* Format: `$((expression))`
* Treats content as double-quoted, but `"` inside is not special.
* Supports signed long integer arithmetic.

## 4. Redirection

Format: `[n]redir-op word`

* `n`: Optional file descriptor number (0-9).
* `redir-op`: Operator.
* `word`: Target (subject to expansion).

### 4.1 Operators

| Operator | Description                                                                            |
| :------- | :------------------------------------------------------------------------------------- |
| `<`    | Redirect Input (FD 0 default)                                                          |
| `>`    | Redirect Output (FD 1 default). Truncates. Fails if `noclobber` set and file exists. |
| `>       | `                                                                                      |
| `>>`   | Append Output.                                                                         |
| `<>`   | Open for Reading and Writing.                                                          |
| `<<`   | Here-Document.                                                                         |
| `<<-`  | Here-Document (strip leading tabs).                                                    |
| `<&`   | Duplicate Input FD.                                                                    |
| `>&`   | Duplicate Output FD.                                                                   |

* If `word` evaluates to `-`, the FD is closed.
* If more than one redirection is specified, evaluation is left-to-right.

## 5. Pattern Matching Notation (Globbing)

Used for Pathname Expansion and `case` statements.

| Pattern   | Meaning                                                             |
| :-------- | :------------------------------------------------------------------ |
| `*`     | Matches any string (including null).                                |
| `?`     | Matches any single character.                                       |
| `[...]` | Bracket expression (matches one char from set/range).`!` negates. |
| `\`     | Escapes the following character.                                    |

**Filename Expansion Rules:**

* `/` must be explicitly matched (not by `*` or `?`).
* Leading `.` in filename must be explicitly matched (not by `*` or `?`).
* If no match found, the pattern string is left unchanged.

## 6. Special Built-In Utilities

These utilities affect the shell environment directly (variable assignments persist). Errors in these may cause the shell to exit (non-interactive).

* `break`, `continue`, `.` (dot), `eval`, `exec`, `exit`, `export`, `readonly`, `return`, `set`, `shift`, `times`, `trap`, `unset`, `:` (colon).

**Parser Note:** Variable assignments preceding a special built-in affect the current environment. Assignments preceding regular utilities affect only the utility's execution environment.

## 7. Error Handling & Exit Status

* **Syntax Error:** Non-interactive shell exits. Interactive shell reports error.
* **Command Not Found:** Exit status 127.
* **Found but Not Executable:** Exit status 126.
* **Signal Termination:** Exit status > 128.
* **Redirection Failure:** Exit status 1-125.
* **Special Built-in Error:** May cause shell exit (non-interactive).

## 8. Implementation Notes for Parser

1. **Line Continuation:** Handle `\` followed by `<newline>` during tokenization (remove both).
2. **Nested Quotes/Substitutions:** Maintain state during tokenization to correctly identify token boundaries (e.g., matching `)` in `$(...)`).
3. **Context Sensitivity:** Reserved words are only recognized in specific contexts (e.g., `in` is only a reserved word after `case` or `for`).
4. **Whitespace:** Generally delimits tokens, except inside quotes or as part of operators.
5. **Ambiguity:** `((` can be arithmetic or grouping. Arithmetic has precedence. Ensure space separation if grouping is intended: `( ( cmd ) )`.
