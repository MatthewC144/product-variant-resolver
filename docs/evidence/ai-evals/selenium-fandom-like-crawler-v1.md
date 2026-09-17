# AI artifact rubric — SEL-CRAWL1 collector and sample workbook

Date:2026-09-16. Engineering fidelity PASS;live source compatibility/permission NOT EVALUATED.

Grounding PASS:the implementation uses the requested Selenium/XLSX technologies and only Fandom-like table
conventions;it does not claim knowledge of the unknown target. Authority PASS:the command requires explicit
operator permission and exact host,while Fandom/Wikia remain unoverrideably denied. Integrity PASS:raw fields,
source URL/title/table/row,time,year filter and parse errors remain auditable beside normalized fields.

Safety PASS for tested scope:one page,no link following,images disabled,no login/proxy/CAPTCHA handling,
cross-host redirect stop and no database/runtime/canonical write. Output fidelity PASS:the public OpenPyXL
runtime path was round-trip tested,and artifact-tool recalculation,formula scan and render inspection completed
for the sample;the three sample rows are synthetic and labeled review-only.
Extendability BOUNDED:header aliases and the row ceiling are explicit,but no pagination,target-specific schema,
robots/terms evidence or 3,000-row performance result exists. Those require a real permitted URL and separate
canary review before execution.
