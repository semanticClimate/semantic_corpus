# Prompt archive — EPMC limit2 fail missing corpora/

**Date:** 2026-11-19  

## Prompt / user report (verbatim)

 ./venv/bin/python scripts/build_example_corpus.py \
>   --config config/epmc_limit2_demo.yaml
Query: ("marine heatwave" OR "ocean heatwave") AND (HAS_FT:Y)
Dates: 2020-01-01 to 2026-12-31
Limit: 2 | Formats: ['xml', 'pdf']
┌─ Europe PMC streams (done)
│ JSON search    active
│ XML full text  active
│ PDF            active
│
│ Finished — no HTTP errors logged.
└─
[epmc] HTTP errors none → /Users/pm286/workspace/semantic_corpus/temp/queries/epmc_limit2_demo/pipeline/epmc_http_errors.json (total=0)
downloaded:
PMC13715829 PMC13672988
Query 'epmc_limit2_demo': 2 results, 2 downloaded -> /Users/pm286/workspace/semantic_corpus/temp/queries/epmc_limit2_demo
Review table: /Users/pm286/workspace/semantic_corpus/temp/queries/epmc_limit2_demo/review/review_table.md
Traceback (most recent call last):
  File "/Users/pm286/workspace/semantic_corpus/scripts/build_example_corpus.py", line 128, in <module>
    main()
  File "/Users/pm286/workspace/semantic_corpus/scripts/build_example_corpus.py", line 110, in main
    corpus = CorpusManager(corpus_dir, use_bagit=True)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/pm286/workspace/semantic_corpus/semantic_corpus/core/corpus_manager.py", line 29, in __init__
    raise CorpusError(
semantic_corpus.core.exceptions.CorpusError: Parent directory does not exist: corpora
