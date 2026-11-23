# Prompt archive — chatbot input contract + session close

**Date:** 2026-11-23  
**Derived docs:**  
- [docs/modules/corpus/siblings.md](../docs/modules/corpus/siblings.md) (diagram: BagIt → fork → text_blocks+metadata → consumers)  
- Related prior: [semantic_corpus/corpus/docs/definitions_text_block.md](../semantic_corpus/corpus/docs/definitions_text_block.md) · [types_io_storage.md](../semantic_corpus/corpus/docs/types_io_storage.md) · [stream_tools.md](../semantic_corpus/corpus/docs/stream_tools.md) · [docs/chatbot_export_contract.md](../docs/chatbot_export_contract.md) (legacy XML/abstract manifest)

---

## Prompts (verbatim, this close)

### Chatbot / corpus output (earlier in session)

We are not yet interested in the chatbot output. Please indicate what corpus output/content we need.

### Chatbot input definition

We will now define chatbot input 
chatbot requires 
* indexed text_blocks
* metadata

This might be directly retrieved from bagit or it might be raw text enhanced by a series of adapters.

Do you agree with this?

**Agent agreed**, with caveat that current `chatbot_manifest` is transitional (XML/abstract paths); long-term input is block index + metadata.

### Siblings diagram

Yes we agree. 
We also believe that some other downstream modules can consume indexed text_blocks. Please redraw the siblings.md to indicate this

Then: The diagram is too complex immediately after bagit. Draw bifurcations after it

### Session finish

we are finishing our session. please summarise current position and I will commit.

have you recorded the latest discussion?

---

## Decisions recorded

1. **Corpus must produce** for chatbot hand-off: BagIt membership, metadata, full text where available, review include-set, search provenance; plus a path to chatbot-facing export. Chatbot UX/answers out of scope.  
2. **Chatbot input (agreed):** indexed **`text_block`s** + **metadata**.  
3. **Two paths:** from BagIt directly, **or** adapters/stream tools enhancing `raw_text` to the same contract.  
4. **Shared consumers:** `phrases_kg`, `encyclopedia`, and `chatbot` all may consume indexed `text_block`s (+ metadata).  
5. **`siblings.md`:** simplified flow — intake → BagIt → fork (bag | adapters) → product → fork to three consumers.  
6. **Transitional:** live export contract still XML/abstract manifest until block-index export is implemented.
