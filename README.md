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
  --max-revisions N   Max revision iterations (0 = unlimited, default from env)
  --non-interactive   Skip review loop
```

### Interactive Review

After generation, the CLI shows a numbered menu:

```
  [1] Approve — finalize and save status.json
  [2] WBS feedback — revise work breakdown
  [3] RAID feedback — revise RAID log
  [4] Both — revise WBS and RAID
  [5] Quit — exit without approving
```

Enter **1–5** when prompted (words like `approve`, `both`, `quit` also work).

Each revision is saved under `versions/vN/`.

## Output Artifacts

| File | Description |
|------|-------------|
| `parsed_brief.json` | Structured extraction from client brief |
| `wbs.json` / `wbs.md` | Work Breakdown Structure |
| `raid.json` / `raid.md` | RAID log (Risks, Assumptions, Issues, Dependencies) |
| `status.json` | Session summary and counts |
| `versions/vN/` | Snapshot after each generation/revision |

## Model

All agents use a single high-accuracy model configured in `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL` | `claude-opus-4-8` | Primary model for brief parsing, WBS, RAID, and revisions |
| `FALLBACK_MODEL` | `gpt-5.5-pro` | Used when `MODEL` is Claude but only `OPENAI_API_KEY` is set |

The provider router sends requests to Anthropic or OpenAI based on the resolved model name. For best results, set `ANTHROPIC_API_KEY` and keep the default Claude Opus model.

## Web UI + API

Start the local server (UI at http://127.0.0.1:8000):

```bash
uv sync --dev
uv run workplan serve
```

Open the UI, paste a brief (or load the sample), and generate. Mock mode works offline; uncheck it and set API keys in `.env` for live runs.

### REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/sessions` | Start generation (`brief_text`, `mock`) |
| `GET` | `/api/sessions/{id}` | Poll session status and artifacts |
| `POST` | `/api/sessions/{id}/review` | Approve or revise (`action`, `feedback`) |

Session artifacts are persisted under `data/sessions/{id}/`.

## Testing

```bash
uv run pytest
```

## Project Structure

```
src/workplan_agent/
├── agents/          # Specialist agents (parser, WBS, RAID, revision)
├── api/             # FastAPI REST layer
├── llm/             # Provider abstraction (OpenAI, Anthropic, mock)
├── models/          # Pydantic schemas
├── static/          # Web UI assets
├── templates/       # Jinja2 Markdown templates
├── orchestrator.py  # Central workflow controller
├── render.py        # JSON/Markdown export
└── cli.py           # Typer CLI entry point
```

## Extension Hooks (Phase 2)

- Stakeholder map and status report agents
- Quality gates checklist
- Optional model overrides per agent type
- Streaming progress and parallel generation where safe
