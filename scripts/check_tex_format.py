"""Static guardrails for the contest LaTeX source; not a TeX compiler."""

from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / "paper" / "ebus_transition.tex"


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    errors = []
    if not re.search(r"\\documentclass\[12pt,letterpaper\]\{article\}", text):
        errors.append("document must use 12pt Letter article")
    # The contest body remains 12 pt. Tables and the reference list use one
    # conventional size reduction so long, numeric material fits the page cap.
    body_text = re.sub(r"\\begin\{table\}.*?\\end\{table\}", "", text, flags=re.S)
    body_text = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "",
                       body_text, flags=re.S)
    body_text = body_text.replace(r"\AtBeginEnvironment{tabular}{\small}", "")
    if re.search(r"\\(?:small|footnotesize|scriptsize|tiny)\b", body_text):
        errors.append("font-size reduction below 12pt found")
    if not all(x in text for x in (r"\pagestyle{fancy}", r"\fancyhead[L]", r"\fancyhead[R]", r"\tableofcontents")):
        errors.append("contest header or contents missing")
    if text.find("Summary Sheet") > text.find(r"\tableofcontents"):
        errors.append("summary must be first")
    if text.find(r"\section*{Report on Use of AI}") < text.find(r"\end{thebibliography}"):
        errors.append("AI report must follow solution/references")
    if r"\src{" in text:
        errors.append("legacy manual citations remain")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in re.finditer(r"(?<!\\)%", line):
            # An unescaped percent after whitespace starts a legitimate source
            # comment. A percent attached to prose or a URL silently truncates
            # the compiled sentence and citation list.
            if match.start() > 0 and not line[match.start() - 1].isspace():
                errors.append(
                    f"raw percent sign must be escaped at line {line_number}"
                )
            break
    defined = set(re.findall(r"\\bibitem\{([^}]+)\}", text))
    cited = {key for group in re.findall(r"\\cite\{([^}]+)\}", text)
             for key in group.split(",")}
    if cited - defined:
        errors.append(f"undefined citations: {sorted(cited-defined)}")
    for graphic in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        target = SOURCE.parent / graphic
        if not target.is_file():
            errors.append(f"missing figure: {graphic}")
    for included in re.findall(r"\\input\{([^}]+)\}", text):
        if not (SOURCE.parent / included).is_file():
            errors.append(f"missing included source: {included}")
    stack = []
    for action, environment in re.findall(r"\\(begin|end)\{([^}]+)\}", text):
        if action == "begin":
            stack.append(environment)
        elif not stack or stack.pop() != environment:
            errors.append(f"unbalanced environment at {environment}")
    if stack:
        errors.append(f"unclosed environments: {stack}")
    if r"\newcommand{\teamnumber}{00000}" in text:
        print("NOTE: replace placeholder control number 00000 before submission")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"STATIC FORMAT PASS: 12pt; {len(defined)} references; "
          f"{len(cited)} cited keys; environments balanced")


if __name__ == "__main__":
    main()
