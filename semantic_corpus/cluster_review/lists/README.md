# Phrase stop / noise lists (Step 2)

Plain-text lists used by `semantic_corpus.cluster_review.step2`.

**Format:** one entry per line, lowercase preferred. Blank lines and `#` comments are ignored.

| File | Purpose |
|------|---------|
| `phrase_boilerplate.txt` | Drop after YAKE/TF-IDF (publishing boilerplate) |
| `latex_noise.txt` | Drop LaTeX / math-mode tokens from TF-IDF |
| `proper_boilerplate.txt` | Drop from capitalized “proper phrase” channel |
| `common_titlecase.txt` | Skip as Titlecase/acronym singles (keep empty or generic) |
| `acronym_skip.txt` | ALLCAPS tokens never treated as phrases |
| `figure_table_noise.txt` | Drop bare fig/eq/table tokens |
| `scientific_discourse.txt` | Drop manuscript discourse (figure, supplementary data, section labels, …) |

Edit these files and re-run phrase extraction (`force=True`) to apply changes.
