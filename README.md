# Consulting Workplan Agent

A multi-agent system that transforms a client brief into consulting deliverables: a Work Breakdown Structure (WBS) and RAID log, with a human-in-the-loop revision cycle.

## Architecture

```
Brief (.md/.txt)
    → OrchestratorAgent
        → BriefParserAgent      → ParsedBrief
        → WBSGeneratorAgent     → WBS
        → RAIDGeneratorAgent    → RAIDLog
        → RevisionAgent         → updated artifacts (on feedback)
    → JSON + Markdown outputs + status.json
```

Specialist agents are stateless; the orchestrator owns session state, versioning, and artifact persistence.

## Quick Start

```bash
# Install dependencies
uv sync --dev

# Offline demo (no API keys required)
uv run workplan run --brief samples/client_brief.md --output ./demo_out/ --mock --non-interactive

# Live run (requires API keys)
cp .env.example .env
# Edit .env with OPENAI_API_KEY and/or ANTHROPIC_API_KEY
uv run workplan run --brief samples/client_brief.md --output ./demo_out/
```

## CLI Usage

```bash
uv run workplan run --brief <path> --output <dir> [options]

Options:
  --mock              Use mock LLM (offline demo)
  --profile TEXT      Model profile: fast | balanced | accurate
  --max-revisions N   Max revision iterations (default: 3)
  --non-interactive   Skip review loop
```

### Interactive Review

After generation, the CLI prompts:

- `[a]` Approve — finalize and write `status.json`
- `[w]` WBS feedback — revise work breakdown
- `[r]` RAID feedback — revise RAID log
- `[b]` Both — revise WBS and RAID
- `[q]` Quit without approving

Each revision is saved under `versions/vN/`.

## Output Artifacts

| File | Description |
|------|-------------|
| `parsed_brief.json` | Structured extraction from client brief |
| `wbs.json` / `wbs.md` | Work Breakdown Structure |
| `raid.json` / `raid.md` | RAID log (Risks, Assumptions, Issues, Dependencies) |
| `status.json` | Session summary and counts |
| `versions/vN/` | Snapshot after each generation/revision |

## Model Profiles

Configure via `.env`:

| Profile | Default model | Used by |
|---------|--------------|---------|
| `fast` | gpt-4o-mini | Future quick drafts |
| `balanced` | gpt-4o | Brief parser, revision |
| `accurate` | claude-sonnet-4-20250514 | WBS, RAID generation |

Override with `MODEL_PROFILE_FAST`, `MODEL_PROFILE_BALANCED`, `MODEL_PROFILE_ACCURATE`.

## Testing

```bash
uv run pytest
```

## Project Structure

```
src/workplan_agent/
├── agents/          # Specialist agents (parser, WBS, RAID, revision)
├── llm/             # Provider abstraction (OpenAI, Anthropic, mock)
├── models/          # Pydantic schemas
├── templates/       # Jinja2 Markdown templates
├── orchestrator.py  # Central workflow controller
├── render.py        # JSON/Markdown export
└── cli.py           # Typer CLI entry point
```

## Extension Hooks (Phase 2)

- Stakeholder map and status report agents
- Quality gates checklist
- FastAPI REST layer + frontend
- User-selectable speed vs accuracy profiles per run
