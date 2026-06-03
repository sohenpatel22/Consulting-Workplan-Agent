# Consulting Workplan Agent

A multi-agent system that transforms a client brief into consulting deliverables: a Work Breakdown Structure (WBS) and RAID log, with a human-in-the-loop revision cycle.

## Architecture

```
Brief (.md/.txt)
    → OrchestratorAgent
        → BriefParserAgent      → ParsedBrief
        → WBSGeneratorAgent     → WBS
        → RAIDGeneratorAgent    → RAIDLog
        → StakeholderAgent      → StakeholderMap
        → StatusReportAgent     → WeeklyStatusReport
        → RevisionAgent         → updated artifacts (on feedback)
    → JSON + Markdown + status.json + Quality Gates Checklists
```

Specialist agents are stateless; the orchestrator owns session state, versioning, and artifact persistence.

## Quick Start

```bash
# Install dependencies
uv sync --dev

# Offline demo (no API keys required)
uv run workplan run --brief samples/client_brief.md --output ./demo_out/ --mock

# Live run (requires API keys)
cp .env.example .env
# Edit .env with OPENAI_API_KEY and/or ANTHROPIC_API_KEY
uv run workplan run --brief samples/client_brief.md --output ./demo_out/
```

## CLI Usage

The CLI is a thin entry point for one-shot generation. Review and revision run in the web UI.

```bash
uv run workplan run --brief <path> --output <dir> [options]

Options:
  --mock              Use mock LLM (offline demo)
  --prompt, -p        Optional planner guidance during generation
```

```bash
uv run workplan serve   # Web UI + REST API (recommended for review)
```

## Output Artifacts

| File | Description |
|------|-------------|
| `parsed_brief.json` | Structured extraction from client brief |
| `wbs.json` / `wbs.md` / `wbs.docx` | Work Breakdown Structure (DOCX uses APS1049 Deloitte table layout) |
| `raid.json` / `raid.md` / `raid.xlsx` | RAID log (XLSX filled from `templates/deloitte/raid_log_template.xlsx`) |
| `stakeholder_map.json` / `stakeholder_map.md` | Stakeholder engagement map and strategy matrix |
| `status_report.json` / `status_report.md` | Weekly status report synced with milestones |
| `quality_gates.json` / `quality_gates.md` | Automated verification checklists and human review sign-offs |
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
├── agents/          # Specialist agents (parser, WBS, RAID, stakeholder, status, revision)
├── api/             # FastAPI REST layer
├── llm/             # Provider abstraction (OpenAI, Anthropic, mock)
├── models/          # Pydantic schemas (WBS, RAID, stakeholder, status, quality gates)
├── static/          # Web UI assets (interactive Quality Gates and checklists)
├── templates/       # Jinja2 Markdown templates (WBS, RAID, stakeholder, status)
├── orchestrator.py  # Central workflow controller
├── render.py        # JSON/Markdown export and Quality Gates validation rules
└── cli.py           # Typer CLI entry point
```

## Deloitte templates (APS1049)

Source files in the project root are synced into machine-readable specs the LLM uses:

```bash
uv run python scripts/sync_deloitte_templates.py
```

This copies source templates into `templates/deloitte/` and writes:

| File | Purpose |
|------|---------|
| `templates/deloitte/wbs_template.spec.json` | Column names, hierarchy rules, example rows from the WBS docx |
| `templates/deloitte/raid_template.spec.json` | Risks / Actions / Issues / Decisions sections from the RAID xlsx |
| `templates/deloitte/stakeholder_template.spec.json` | Stakeholder map columns and example rows from the stakeholder xlsx |
| `templates/deloitte/status_report_template.spec.json` | Status report sections and milestone table from the status docx |

`prompts.py` injects these specs into every WBS, RAID, Stakeholder Map, and Weekly Status Report generation call (plus the Pydantic JSON schema). Generated data uses the same field names as the templates (`wbs_code`, `wbs_links`, `engagement_strategy`, `milestones`, etc.).

**RAID categories:** Risks, **Actions**, Issues, **Decisions** (not Assumptions/Dependencies). Legacy `items` JSON is still accepted when loading old sessions.

Exports: `wbs.docx` and `raid.xlsx` fill the Deloitte layouts; download **XLSX** on the RAID tab in the UI.

## Quality Gates & Verification

The pipeline incorporates **Quality Gates** to ensure deliverable alignment before final Engagement Manager approval:
- **Automated Validation**: Verifies parent-child WBS codes, RAID-to-WBS links, stakeholder manager alignment, and status report milestone synchronization.
- **Reference Guide**: [QUALITY_GATES.md](file:///c:/Users/ASUS/Desktop/UofT/Summer%202026/APS1049%20Managment%20Consultants/Deloitte%20Engagement%20Manager%20Agent%20Project/Updated%20My%20Part/Antigravity/IDE/1049-deloitte-project/QUALITY_GATES.md) defines validation tasks and failure modes.
- **Interactive UI tab**: Facilitates human sign-offs on manual quality gate checks (durations, role mappings, and RAG status).
