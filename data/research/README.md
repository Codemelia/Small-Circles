# Research outputs

This folder holds **search results** used to design CBT-informed facilitation (not clinical protocols).

| What | Where |
|---|---|
| How to run a literature search | [`scripts/lit_search_openalex.py`](../../scripts/lit_search_openalex.py) |
| Search query config | [`scripts/lit_search_queries.json`](../../scripts/lit_search_queries.json) |
| Design notes from screening | [`docs/cbt-informed-research.md`](../../docs/cbt-informed-research.md) |
| Prompts/experiments informed by that work | [`data/interventions/cbt_informed.json`](../interventions/cbt_informed.json) |
| How the CLI uses those libraries | [`docs/agentic-cli-demo.md`](../../docs/agentic-cli-demo.md) |
| Target system design & stack | [`docs/system-design.md`](../../docs/system-design.md) |

After you run a search, CSV/JSON dumps appear here (they are gitignored — regenerate anytime):

```powershell
python scripts/lit_search_openalex.py --mailto you@example.com
```
