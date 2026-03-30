from __future__ import annotations

from dataclasses import dataclass

from .model import HeredocRecord


@dataclass(slots=True)
class PendingHeredoc:
    delimiter: str
    quoted: bool
    start_line: int


class HeredocParser:
    def extract(self, source: str) -> list[HeredocRecord]:
        lines = source.splitlines()
        out: list[HeredocRecord] = []
        pending: list[PendingHeredoc] = []

        line_no = 0
        while line_no < len(lines):
            line = lines[line_no]
            self._collect_headers(line, line_no + 1, pending)
            line_no += 1

            while pending and line_no < len(lines):
                current = pending[0]
                body_lines: list[str] = []
                while line_no < len(lines):
                    candidate = lines[line_no]
                    if candidate == current.delimiter:
                        out.append(
                            HeredocRecord(
                                delimiter=current.delimiter,
                                quoted=current.quoted,
                                body="\n".join(body_lines),
                                start_line=current.start_line,
                                end_line=line_no + 1,
                            )
                        )
                        line_no += 1
                        pending.pop(0)
                        break
                    body_lines.append(candidate)
                    line_no += 1
                else:
                    pending.pop(0)

        return out

    def _collect_headers(self, line: str, line_no: int, pending: list[PendingHeredoc]) -> None:
        idx = 0
        while idx < len(line):
            pos = line.find("<<", idx)
            if pos < 0:
                return
            j = pos + 2
            if j < len(line) and line[j] == "-":
                j += 1
            while j < len(line) and line[j].isspace():
                j += 1
            if j >= len(line):
                return

            quoted = line[j] in {'\"', "'"}
            if quoted:
                quote = line[j]
                j += 1
                k = line.find(quote, j)
                if k < 0:
                    return
                delim = line[j:k]
                idx = k + 1
            else:
                k = j
                while k < len(line) and not line[k].isspace() and line[k] not in ";|&":
                    k += 1
                delim = line[j:k]
                idx = k

            if delim:
                pending.append(PendingHeredoc(delimiter=delim, quoted=quoted, start_line=line_no))
