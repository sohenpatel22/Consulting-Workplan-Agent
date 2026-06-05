# Project Build Path and Methodology

## Purpose

- This document explains how the Deloitte Workplan Agent project was built from the ground up.
- It is written as a slide-friendly project narrative for a professor or supervisor.
- It focuses on:
  - The project path from initial setup to final system.
  - The engineering and AI methodologies used.
  - The experiments, ablation studies, and design choices made during development.

## Project Goal

- Build an AI-assisted consulting workplan system for Deloitte-style project planning.
- Convert a client brief into structured consulting deliverables:
  - Work Breakdown Structure (WBS)
  - RAID log
  - Stakeholder map
  - Weekly status report
  - Quality gates checklist
- Support both:
  - Automated generation using LLM agents.
  - Human-in-the-loop review and revision.
- Align generated outputs with real Deloitte project templates.

## High-Level Build Path

- The project was built in several stages:
  - Start with a command-line prototype.
  - Add structured LLM agents and Pydantic schemas.
  - Add a web UI and FastAPI backend.
  - Add file upload, extraction, and export features.
  - Ground generation in real Deloitte templates.
  - Add confirmation questions before generation.
  - Add stakeholder map, status report, and quality gates.
  - Improve revision UX, streaming, exports, and architecture documentation.

## Phase 0: Initial Setup

- Created the Python project structure using `uv`.
- Added core project configuration:
  - `pyproject.toml`
  - `.python-version`
  - `uv.lock`
  - `main.py`
- Created the main package:
  - `src/workplan_agent/`
- Established a simple starting point for running the system locally.
- Main objective:
  - Build a clean technical foundation before adding AI workflow logic.

## Phase 1: CLI Prototype

- Built the first working prototype as a command-line tool.
- Added the CLI entry point:
  - `src/workplan_agent/cli.py`
- Added a sample client brief:
  - `samples/client_brief.md`
- Built the first generation workflow:
  - Input: client brief
  - Processing: parse brief, generate WBS, generate RAID
  - Output: JSON and Markdown artifacts
- Created the first orchestration layer:
  - `src/workplan_agent/orchestrator.py`
- Main objective:
  - Prove that a client brief could be transformed into useful consulting deliverables.

## Phase 2: Multi-Agent Architecture

- Split the workflow into specialist agents.
- Added agents for different responsibilities:
  - `BriefParserAgent`
  - `WBSGeneratorAgent`
  - `RAIDGeneratorAgent`
  - `RevisionAgent`
- Agent files:
  - `src/workplan_agent/agents/brief_parser.py`
  - `src/workplan_agent/agents/wbs_generator.py`
  - `src/workplan_agent/agents/raid_generator.py`
  - `src/workplan_agent/agents/revision.py`
  - `src/workplan_agent/agents/base.py`
- Design decision:
  - Keep specialist agents mostly stateless.
  - Let the orchestrator manage workflow state.
- Main objective:
  - Make the system modular and easier to extend with new deliverables.

## Phase 3: Structured Data Models

- Added Pydantic models to make LLM outputs structured and validated.
- Core models:
  - `src/workplan_agent/models/brief.py`
  - `src/workplan_agent/models/wbs.py`
  - `src/workplan_agent/models/raid.py`
  - `src/workplan_agent/models/session.py`
- Methodology:
  - Do not rely only on free-form LLM text.
  - Ask the LLM for structured JSON.
  - Validate that JSON against schemas.
  - Render validated data into reports.
- Main objective:
  - Improve reliability, consistency, and testability.

## Phase 4: LLM Provider Layer

- Added a provider abstraction for different LLM services.
- Supported providers:
  - OpenAI
  - Anthropic
  - Mock provider for offline testing
- Key files:
  - `src/workplan_agent/llm/base.py`
  - `src/workplan_agent/llm/openai_provider.py`
  - `src/workplan_agent/llm/anthropic_provider.py`
  - `src/workplan_agent/llm/mock_provider.py`
  - `src/workplan_agent/llm/routing_provider.py`
  - `src/workplan_agent/config.py`
- Methodology:
  - Separate business workflow from model vendor details.
  - Allow the same agents to run on different model backends.
  - Use a mock provider to test the pipeline without paid API calls.

## Phase 5: Rendering and Templates

- Added Markdown rendering for generated artifacts.
- Initial templates:
  - `src/workplan_agent/templates/wbs.md.j2`
  - `src/workplan_agent/templates/raid.md.j2`
- Rendering logic:
  - `src/workplan_agent/render.py`
- Methodology:
  - Separate data generation from presentation.
  - Keep generated content structured before converting it into human-readable reports.
- Main objective:
  - Make outputs easy to review, export, and revise.

## Phase 6: Testing from Early Development

- Added tests for the early prototype and core agents.
- Early test coverage included:
  - Brief parsing
  - WBS generation
  - RAID generation
  - Orchestration
  - Revision logic
  - LLM routing
- Test files included:
  - `tests/test_brief_parser.py`
  - `tests/test_wbs_generator.py`
  - `tests/test_raid_generator.py`
  - `tests/test_orchestrator.py`
  - `tests/test_revision.py`
  - `tests/test_routing_provider.py`
- Methodology:
  - Use mock LLM outputs for deterministic tests.
  - Test schemas and workflow behavior, not only UI behavior.

## Phase 7: Web UI and API

- Added a FastAPI backend and browser-based UI.
- API layer:
  - `src/workplan_agent/api/app.py`
  - `src/workplan_agent/api/service.py`
  - `src/workplan_agent/api/schemas.py`
  - `src/workplan_agent/api/store.py`
- Frontend:
  - `src/workplan_agent/static/index.html`
  - `src/workplan_agent/static/app.js`
  - `src/workplan_agent/static/style.css`
- Features added:
  - Paste or load a client brief.
  - Start a generation session.
  - View generated artifacts.
  - Submit review feedback.
  - Revise generated reports.
- Methodology:
  - Move from a developer-only CLI to an interactive workflow for business users.
  - Treat each generation run as a session with persisted state.

## Phase 8: File Upload and Export

- Added file upload and extraction.
- Added export support for generated outputs.
- Key files:
  - `src/workplan_agent/api/files.py`
  - `src/workplan_agent/files/extract.py`
  - `src/workplan_agent/files/export.py`
  - `src/workplan_agent/files/pdf_render.py`
- Supported input/output direction:
  - Input: Markdown, text, PDF, DOCX
  - Output: Markdown, HTML, PDF, DOCX, XLSX where supported
- Methodology:
  - Support realistic consulting workflows where briefs and deliverables are documents, not just text fields.

## Phase 9: Prompt Engineering and Prompt Cache

- Centralized prompt construction:
  - `src/workplan_agent/prompts.py`
- Added explicit prompt sections for:
  - Brief parsing
  - WBS generation
  - RAID generation
  - Revision
  - Stakeholder map generation
  - Status report generation
- Added prompt caching:
  - `src/workplan_agent/llm/caching.py`
  - `src/workplan_agent/llm/cache_warmup.py`
- Methodology:
  - Reuse stable prompt context across similar calls.
  - Reduce latency and cost where the same brief/template context is reused.
  - Keep prompt behavior centralized and easier to audit.

## Phase 10: Deloitte Template Grounding

- Added real Deloitte / APS1049 template files.
- Source templates included:
  - WBS template explanation DOCX
  - RAID log XLSX
  - Stakeholder map XLSX
  - Weekly status report DOCX
- Template sync and extraction:
  - `scripts/sync_deloitte_templates.py`
  - `src/workplan_agent/files/template_extract.py`
- Machine-readable template specs:
  - `src/workplan_agent/templates/deloitte/wbs_template.spec.json`
  - `src/workplan_agent/templates/deloitte/raid_template.spec.json`
  - `src/workplan_agent/templates/deloitte/stakeholder_template.spec.json`
  - `src/workplan_agent/templates/deloitte/status_report_template.spec.json`
- Deloitte export logic:
  - `src/workplan_agent/files/deloitte_export.py`
- Methodology:
  - Use real templates as grounding data.
  - Extract column names, examples, and structure from templates.
  - Inject template specs into prompts.
  - Make LLM output match required Deloitte deliverable formats.

## Phase 11: Confirmation Questions Before Generation

- Added a confirmation stage before generating final deliverables.
- The system parses the brief first.
- If important information is missing, it asks the user clarification questions.
- Key files:
  - `src/workplan_agent/confirmation.py`
  - `src/workplan_agent/models/brief.py`
  - `src/workplan_agent/api/service.py`
  - `src/workplan_agent/static/app.js`
- Features:
  - Open questions generated from incomplete brief information.
  - Optional multiple-choice answers.
  - Confirmation state in the UI.
  - Cache warmup while waiting for user answers.
- Methodology:
  - Avoid generating weak deliverables from incomplete inputs.
  - Ask the user for clarification before spending model calls on full report generation.

## Phase 12: Phase 2 Deliverables

- Expanded from two deliverables to four main consulting outputs.
- Added:
  - Stakeholder map
  - Weekly status report
  - Quality gates checklist
- New agents:
  - `src/workplan_agent/agents/stakeholder_generator.py`
  - `src/workplan_agent/agents/status_generator.py`
- New models:
  - `src/workplan_agent/models/stakeholder.py`
  - `src/workplan_agent/models/status_report.py`
  - `src/workplan_agent/models/quality_gates.py`
- New templates:
  - `src/workplan_agent/templates/stakeholder_map.md.j2`
  - `src/workplan_agent/templates/status_report.md.j2`
- Methodology:
  - Reuse the same architecture pattern:
    - Agent
    - Prompt
    - Pydantic model
    - Template
    - Tests
  - Extend the system without rewriting the core orchestration approach.

## Phase 13: Quality Gates and Failure Modes

- Added automated and human quality checks.
- Documentation:
  - `QUALITY_GATES.md`
- Automated validation examples:
  - WBS parent-child code validation
  - RAID-to-WBS traceability
  - Stakeholder role consistency
  - Status report milestone alignment
- Human review examples:
  - Validate duration realism.
  - Confirm risk vs issue classification.
  - Confirm stakeholder influence/interest mapping.
  - Confirm RAG status is justified.
- Failure modes documented:
  - WBS parent code mismatch
  - Orphaned RAID mappings
  - Duration overrun
  - Misaligned RAG status
  - Stakeholder omission
- Methodology:
  - Treat LLM output as something that must be validated.
  - Combine automated checks with Engagement Manager sign-off.

## Phase 14: Revision UX and Artifact Versioning

- Improved the human-in-the-loop revision process.
- Added per-artifact revision tracking:
  - `src/workplan_agent/models/artifact_versions.py`
- Supported revision of individual artifacts:
  - WBS
  - RAID
  - Stakeholder map
  - Status report
  - Quality gates
- Added dependency-aware versioning:
  - Example: revising the WBS can affect RAID links or status milestones.
- Methodology:
  - Make review targeted instead of forcing full regeneration every time.
  - Track how artifact versions change over time.
  - Preserve session history for auditability.

## Phase 15: Streaming and UI Polish

- Added streaming report generation.
- Improved UI responsiveness during long-running LLM calls.
- Added fullscreen report preview.
- Simplified revision workflow in the UI.
- Fixed PDF export behavior.
- Key files:
  - `src/workplan_agent/api/service.py`
  - `src/workplan_agent/static/app.js`
  - `src/workplan_agent/static/style.css`
  - `src/workplan_agent/files/pdf_render.py`
- Methodology:
  - Improve perceived performance.
  - Make the tool easier for non-technical users to review.

## Phase 16: Architecture Documentation

- Added architecture diagrams and generated Mermaid charts.
- Files:
  - `architecture_charts/ARCHITECTURE.md`
  - `architecture_charts/ARCHITECTURE.mmd`
  - `architecture_charts/ARCHITECTURE_SIMPLE.md`
  - `architecture_charts/ARCHITECTURE_SIMPLE.mmd`
  - `architecture_charts/generate_architecture_graph.py`
  - `architecture_charts/generate_simple_architecture_graph.py`
- Methodology:
  - Maintain both technical and business-facing architecture views.
  - Use diagrams to explain the system flow from inputs to generated reports.

## Model Ablation Studies

- The project tested different LLM model choices over time.
- Goal of ablation:
  - Compare quality, cost, latency, and reliability.
  - Keep the workflow constant while changing the model.
- Models/configurations explored:
  - High-accuracy Claude model for Deloitte-quality outputs.
  - Smaller OpenAI model for cost and speed experiment.
  - Claude Sonnet model as a balance between cost and quality.
  - Claude Haiku model in current working tree for further cost/speed testing.
- Key file:
  - `src/workplan_agent/config.py`
- Ablation methodology:
  - Keep the same agents, schemas, prompts, and templates.
  - Change only the configured model.
  - Evaluate generated deliverables for:
    - Completeness
    - Template alignment
    - Consulting language quality
    - Schema validity
    - Speed
    - Cost
- Finding:
  - Smaller models are faster and cheaper.
  - Larger models tend to produce stronger consulting reasoning and more complete outputs.
  - Template grounding and strict schemas reduce the quality gap between models.

## Prompt and Template Ablation

- The project also evolved prompt and template strategies.
- Early approach:
  - Prompt the model to generate reports using general instructions.
- Improved approach:
  - Inject Pydantic JSON schema.
  - Inject Deloitte template specs.
  - Add strict grounding rules.
  - Add role split and template-specific field names.
- Compared approaches:
  - Free-form markdown generation.
  - Structured JSON generation followed by rendering.
  - Template-guided structured generation.
- Finding:
  - Free-form markdown is easier to start with but harder to validate.
  - Structured JSON is more reliable for testing and downstream exports.
  - Template-guided generation produces outputs closer to Deloitte expectations.

## Revision Methodology

- Initial revision approach:
  - General review and revise workflow.
- Later revision approach:
  - Web-based artifact-specific feedback.
  - Version tracking for each artifact.
  - Dependency-aware updates.
- Benefits:
  - Easier for reviewers to give precise feedback.
  - Easier to see which report changed.
  - Better support for iterative improvement.

## Testing Methodology

- Tests were added throughout the project rather than only at the end.
- Main testing categories:
  - Agent output tests
  - Schema validation tests
  - API tests
  - File upload/export tests
  - Template extraction tests
  - Quality gate tests
  - Confirmation question tests
  - Artifact versioning tests
- Important test files:
  - `tests/test_api.py`
  - `tests/test_files.py`
  - `tests/test_quality_gates.py`
  - `tests/test_deloitte_templates.py`
  - `tests/test_confirmation.py`
  - `tests/test_artifact_versions.py`
- Methodology:
  - Use mock providers for deterministic tests.
  - Test system behavior independent of live API keys.
  - Validate that generated artifacts conform to expected schemas.

## Final System Architecture

- Input layer:
  - Client brief
  - Optional user guidance
  - Confirmation answers
  - Reviewer feedback
- Entry points:
  - Web UI
  - FastAPI API
  - CLI for simple runs
- Orchestration:
  - `OrchestratorAgent` controls the workflow.
  - Session model stores intermediate and final artifacts.
- Specialist agents:
  - Brief parser
  - WBS generator
  - RAID generator
  - Stakeholder generator
  - Status report generator
  - Revision agent
- Output layer:
  - JSON
  - Markdown
  - DOCX
  - XLSX
  - PDF / HTML where applicable
  - Quality gates checklist

## Current Key Paths

- Main package:
  - `src/workplan_agent/`
- Agents:
  - `src/workplan_agent/agents/`
- API:
  - `src/workplan_agent/api/`
- Frontend:
  - `src/workplan_agent/static/`
- LLM providers:
  - `src/workplan_agent/llm/`
- Pydantic models:
  - `src/workplan_agent/models/`
- Prompt logic:
  - `src/workplan_agent/prompts.py`
- Deloitte templates:
  - `src/workplan_agent/templates/deloitte/`
- Rendering:
  - `src/workplan_agent/render.py`
- File extraction/export:
  - `src/workplan_agent/files/`
- Architecture diagrams:
  - `architecture_charts/`
- Tests:
  - `tests/`

## Slide-Friendly Summary

- Started with a minimal Python/uv project.
- Built a CLI prototype to prove brief-to-report generation.
- Introduced a multi-agent design for modularity.
- Added Pydantic schemas to make LLM output structured and validatable.
- Added OpenAI, Anthropic, and mock LLM providers.
- Added Markdown rendering with Jinja templates.
- Added tests early to stabilize the pipeline.
- Built a FastAPI backend and web UI for interactive use.
- Added file upload, document extraction, and report export.
- Grounded outputs in real Deloitte templates.
- Added confirmation questions to improve input quality.
- Expanded deliverables from WBS/RAID to stakeholder map and status report.
- Added quality gates for automated validation and human sign-off.
- Added artifact versioning and targeted revision.
- Conducted model ablation studies for quality/cost/speed tradeoffs.
- Documented the final architecture with Mermaid diagrams.

## Suggested Slide Structure

- Slide 1: Project goal and motivation
- Slide 2: Final system overview
- Slide 3: Build path from CLI prototype to web app
- Slide 4: Multi-agent architecture
- Slide 5: Structured JSON and Pydantic validation methodology
- Slide 6: Deloitte template grounding
- Slide 7: Human-in-the-loop confirmation and revision
- Slide 8: Quality gates and failure modes
- Slide 9: Model and prompt ablation studies
- Slide 10: Testing methodology
- Slide 11: Final outputs and demo workflow
- Slide 12: Lessons learned and future improvements

## Future Improvements

- Add more quantitative evaluation metrics for output quality.
- Record side-by-side model comparison results for ablation studies.
- Add automatic scoring for consulting deliverable quality.
- Add stronger traceability from brief sentence to generated artifact field.
- Add deployment documentation for non-local use.
- Add richer UI for comparing artifact versions.
