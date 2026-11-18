# Prompt archive — corpus design (continuation)

**Date:** 2026-11-18  
**Follows:** [prompt_2026-11-18_corpus_design.md](prompt_2026-11-18_corpus_design.md)  
**Derived design:** [docs/modules/corpus/design.md](../docs/modules/corpus/design.md)

---

## Prompt (verbatim)

[... ]
* the processing will use a doit-like strategy. if an ingest is terminated, then a rerun will detect satisfactorily ingested entries and skip them. 
* ingestion of non-semantic material can trigger cleaning and semantifucation. Examples include converting PDF or DOCx to HTML, and cleaning HTML (either from conversion or from web pages (Gatsby, Wordpress) ) to create structured HTML with IDs
* ingestion will be compatible with BAGIT and may additonal need to conform to user schema.

Typical ingested material includes:
* queries to scholarly repositires (EPMC, Redalyc - but there will be a separate module for gather and semantify)
* theses
* reports (IPCC, etc.)

`corpus` will have ingest hooks that can be used/adapted by the `repository` module . It might come with an example for EPMC and instructions/code to build others

We might need to have a librray of declarative cleaners (docling/PDF, OOXML/WordHTML/DOCx, Gatsby, Wordpress )

We need an HTML table display so users can manually Browse, Read, Delete the contents and search by regex of filenames or contents.

(There may be other functionality  I have overlooked.

Please formlaize this specification and then indicate any potentially overlapping og complementary tools of approcahes. Not that `corpus` is primarily for. personal copora and not for production maintenance of instituional repositories
