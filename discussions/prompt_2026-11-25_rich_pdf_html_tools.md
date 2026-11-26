# Prompt archive — rich PDF/HTML needs vs OSS / amilib

**Date:** 2026-11-25  
**Derived:** [semantic_corpus/corpus/docs/input_adapters.md](../semantic_corpus/corpus/docs/input_adapters.md) §8 · [examples/pdf_html_compare/README.md](../examples/pdf_html_compare/README.md)

## Prompt (verbatim)

OK - you have a long way to go. 
Your HTML is essentially the screen characters as lines.
We need a lot more.
* line joins
* sub-and superscripts
*  headers and footers
* footnotes
* lists
* fonts
* recognition of tables
* recognition of figures

Are there any open source tools which provide some/all of these? 
I wrote my own in amilib. If there are no other equivalenrs we will need to use and update amilib.

most of these concerns will also apply to hOCR output .
