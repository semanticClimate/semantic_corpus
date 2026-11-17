# `<module_name>` — template

Replace this file when copying `module_template/` to a real module.

1. Set fields in `module.yaml` (see `../MODULE_SPEC.md`).  
2. Add `docs/modules/<module_name>/overview.md` matching the yaml `docs` path.  
3. Export the public API from `__init__.py`.  
4. Register the directory name in `semantic_corpus.module_meta.REGISTERED_MODULES`.  
5. List facilities users can invoke; keep summaries to one line each.

**Owner:** (fill in)  
**Status:** extension  
**Depends on:** corpus (usually)
