## Key points of discussion

## 19-11-2026

#### Purpose

To review the overall strategy for a modular toolkit for building and querying personal research corpora; to assign module ownership; to demonstrate declarative (YAML-driven) ingestion; and to plan next steps toward a journal submission.

#### Architecture

The system has five modules. Each should work on its own and pass information to the others as text, like Unix tools.
Each module should work standalone. For example, you could query repositories without a corpus, or run a chatbot without one, but a corpus makes each of them better.

#### Theses as a data source

About half a million Indian theses are available via a national repository and are currently poorly reused. As examined, peer-reviewed documents, they are a valuable query target alongside Europe PMC. Similar national repositories in Latin America should be investigated. National repositories are easier to work with than separate repositories for each of roughly 1,000 to 2,000 research universities.

#### Demonstration of declarative ingestion
- A YAML file specifies the query name, query string, repository (Europe PMC) and date range. No Python changes are needed.
- The run performs a Boolean search, downloads a specified number of papers (two in the demonstration), builds a review table, and ingests the results into the corpus.
- The tool is intended as an upgrade to the older getpapers tool.
- Europe PMC's full-text filter (FT:Y) was shown.
- Output includes SHA-256 hashes for integrity checking.

#### Open design questions

When a query is re-run with a higher paper count, should the tool add to, overwrite, or skip existing papers? The best user interface and strategy were also left open for input from all members.

## 17-11-2026
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
