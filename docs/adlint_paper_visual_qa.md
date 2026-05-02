# AdLint Paper Visual QA

## Final Build Evidence

- Source reviewed: `docs/adlint_hybrid_eval_paper.tex`
- Output reviewed: `docs/build/adlint_hybrid_eval_paper.pdf`
- Bundled Tectonic: `/Users/ftchvs/Developer/.agents/codex/plugins/cache/openai-bundled/latex-tectonic/0.1.0/bin/tectonic`
- Compile command, run from `/Users/ftchvs/Developer/AdLint`:

```bash
/Users/ftchvs/Developer/.agents/codex/plugins/cache/openai-bundled/latex-tectonic/0.1.0/bin/tectonic --outdir docs/build docs/adlint_hybrid_eval_paper.tex
```

- Compile result: passed; PDF written to `docs/build/adlint_hybrid_eval_paper.pdf`.
- Render verification: `uv run --with pypdfium2 --with pillow ...`
- Final rendered page count: 5 pages.

## Final Visual Checks

- Page 1 title, subtitle, abstract, and opening sections render cleanly with no clipping.
- Page 2 architecture diagram stays inside margins and no connector line crosses node text.
- Figures use final-size PGFPlots/TikZ text rather than post-hoc `resizebox` scaling.
- Charts have readable axis labels, visible category labels, and direct value labels.
- Tables stay inside the text block with consistent booktabs rules and numeric alignment.
- The previous float-only/orphan page is gone; the paper ends with substantive content on page 5.
- Headers, footers, and page numbers are consistent across paginated pages.

## Remaining Notes

- Tectonic still emits font lookup chatter for downloaded font assets; it does not block PDF generation.
- One minor underfull paragraph warning remains around the all-modes-runner description, but the rendered spacing is acceptable.
