## Key points of discussion

- **Project structure (proposed split into ~5 papers)**

    - Corpus (core): repository structure (BagIt), ingest from literature search and static resources, and the “DOIt” pipeline. This is the first paper and the template for the others.
    - Repositories: connectors for PubMed Central, OpenAlex, SciELO, and others, with an emphasis on Global South repositories like CONICET
    - Phrases & knowledge graph
    - Encyclopedia
    - ClimateInsight Chatbot

- **Design principles**

    - All information is semantic, with a clear type and ID, in meaningful chunks (paragraphs, tables).
    - It follows an incremental “DOIt” approach: new data updates the repository, and incomplete data gets processed.
    - Code is declarative where possible (JSON/YAML templates, external HTML/CSS/JS), so people can edit templates locally without touching the core.
    - Search is text-based for now.

- **JOSS paper requirements**

    - Paper sections: title, authors and affiliations, summary, statement of need, state of the field, software design, research impact, AI usage disclosure, and references.

    - Reviewer checklist: software available, licensed, installable, examples show it works, sustained development (about 6 months or more), open development, community engagement, reproducible results, no original data.

    - Reviewers must be human. AI is only allowed for non-substantive help.
