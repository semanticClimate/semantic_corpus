# Prompt archive — repositories submodule strategy

**Date:** 2026-11-19  
**Derived docs:** [docs/modules/repositories/strategy.md](../docs/modules/repositories/strategy.md)

## Prompt (verbatim)

Please change focus to `repository` submodule. This will search a variety of repositories with a text query, preferably Boolean, and additional date constraints. Much of the logic is already in `pygetpapers`. 
This should be declarative, i.e. a user can add a new repository without editing Python code. The logic should deal with different states of the server (e.g. codes 403) and give examples of timing if requested.

Please outline a complete strategy here but do not write code
