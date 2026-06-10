from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, WBS_FIXTURE
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.render import render_wbs_html, render_wbs_markdown


def test_wbs_markdown_marks_confirmed_items() -> None:
    parsed = ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)
    wbs = WBS.model_validate(WBS_FIXTURE)
    markdown = render_wbs_markdown(wbs, parsed)
    assert "confirmed planner questions" in markdown
    assert "3.2*" in markdown


def test_wbs_html_marks_confirmed_rows() -> None:
    parsed = ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)
    wbs = WBS.model_validate(WBS_FIXTURE)
    html = render_wbs_html(wbs, parsed)
    assert 'class="from-confirmed"' in html
    assert "confirmed planner questions" in html
