# Planning documents

Design and build plan for the HarborRAG documentation website. These are working documents for the team; the Confluence pages of the same names are the reviewed copies, and the two should be kept in step.

| File | What it is | Read when |
|---|---|---|
| `01_Sync_Architecture.md` | The design: two repos, `repository_dispatch` from HarborRAG, ingest, versioned snapshots, tokens, failure modes, migration | You need to know *why* something is the way it is |
| `02_Scaffold_and_Build_Guide.md` | The shape: repo layout, Docusaurus config, ingest script spec, workflow YAML, settings checklist, cut-over | You need the reference version of a file or a table |
| `03_Implementation_Plan.md` | The order: phases → numbered steps, each with files touched, commands, an exit check and a commit message; plus the status board | You are about to write code |

These live under `docs/planning/` at the repository root on purpose — outside `website/`, so Docusaurus never picks them up as site content.

## Working with Claude on this

Open `03_Implementation_Plan.md`, find the step you are on, and start the conversation with the step number and what you have ("I'm at 2.7, here is my `links.py` and the failing test"). Each step is written to be self-contained enough that the conversation can stay on that step. When a step changes a decision recorded in `01` or `02`, update those files in the same commit and mirror the change to Confluence.

## Status

See the status board at the end of `03_Implementation_Plan.md`. Update it in the same commit as the step it describes.
