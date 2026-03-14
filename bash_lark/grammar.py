GRAMMAR = r"""
start: script
script: statement*

statement: command terminator?
         | terminator
terminator: SEP

command: command_item+
?command_item: assignment_word | redirection | word

redirection: IO_NUMBER? REDIR_OP redir_target
assignment_word: NAME "=" word?
redir_target: PROCESS_SUBST | word
word: WORD

SEP: /(?:\r?\n)+|;+|&+|\|\||&&|\|/
REDIR_OP: "<<-"|"<<"|">>"|"<>"|">|"|"<&"|">&"|"<"|">"
IO_NUMBER: /[0-9]+/
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
PROCESS_SUBST: /[<>]\([^\n)]*\)/
WORD: /(?:\\.|\$\([^\n)]*\)|`[^`\n]*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s;|&<>])+/

%ignore /[ \t\f]+/
%ignore /#[^\n]*/
"""
