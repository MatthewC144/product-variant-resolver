# SEL-CRAWL1 implementation evidence

Date:2026-09-16. Mode:Lite. Scope:one permitted non-Fandom page to review-only XLSX.

## Observable result

- Source guard requires `--start-url`,`--allowed-host` and `--confirm-permission`;Fandom/Wikia have no override.
- Selenium Chrome reads only Fandom-like text tables,waits for dynamic DOM and disables image downloads.
- Header-based normalization retains explicit color and splits suffixes such as `2nd Color - Zamac` without
  inventing color from filenames or edition markers.
- The workbook has `Summary` and `Releases`,filters,frozen headers,source/raw/error fields and computed counts.

## Verification

The focused run passed four pure unit tests,one real Selenium/Chrome smoke test against the local delayed HTML
fixture,and one checked-in workbook structure test. It exported three 2025 rows and excluded one 2024 row.
The portable OpenPyXL path was loaded back and checked for sheets,formula,text identifier and frozen pane.
Artifact-tool XLSX inspection found three records,zero
parse errors and zero formula-error matches. Both worksheets rendered without clipped summary content;
identifier cells are stored as XLSX strings (`t="str"`) and UTC cells use an explicit date-time format.

The final full test suite passed615 tests with the opt-in browser test skipped and one existing
Starlette/AnyIO deprecation warning. The separate focused run enabled the browser test and passed all6
feature checks. Focused Ruff/strict MyPy,compileall,Node syntax and JSON parsing also passed. A first full
pytest command without `PYTHONPATH=src` exposed the repository's existing subprocess-import environment
requirement;rerunning with that documented path passed. Repository-wide Ruff/MyPy have pre-existing unrelated
debt,so the scoped clean result applies to the new collector files rather than claiming a clean whole repo.

## Limitations

No remote request occurred. The future target's terms,robots policy,exact headers,pagination and challenge
behavior are not evaluated. The sample workbook contains only synthetic `example.test` records and cannot be
reported as catalog growth,reviewed variants,canonical products or Dual RAG evidence.
