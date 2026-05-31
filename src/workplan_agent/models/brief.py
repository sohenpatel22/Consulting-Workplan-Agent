from pydantic import BaseModel, Field


class Objective(BaseModel):
    id: str
    description: str
    success_criteria: str = ""


class Constraint(BaseModel):
    type: str
    description: str


class Stakeholder(BaseModel):
    name: str
    role: str
    interest: str = ""


class Timeline(BaseModel):
    start: str = ""
    end: str = ""
    milestones: list[str] = Field(default_factory=list)


class ResolvedQuestion(BaseModel):
    question: str
    answer: str


class ParsedBrief(BaseModel):
    client_name: str
    project_title: str
    background: str = ""
    objectives: list[Objective]
    scope_in: list[str]
    scope_out: list[str] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    assumptions_from_brief: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    resolved_open_questions: list[ResolvedQuestion] = Field(default_factory=list)

    def apply_open_question_resolutions(self, answers: list[ResolvedQuestion]) -> None:
        pending = list(self.open_questions)
        if not pending:
            raise ValueError("No open questions to resolve.")
        if len(answers) != len(pending):
            raise ValueError(
                f"Expected {len(pending)} answer(s), got {len(answers)}."
            )
        answer_by_question = {item.question: item.answer.strip() for item in answers}
        for question in pending:
            if question not in answer_by_question:
                raise ValueError(f"Missing answer for open question: {question}")
            if not answer_by_question[question]:
                raise ValueError(f"Answer cannot be empty for: {question}")

        for question in pending:
            answer = answer_by_question[question]
            self.resolved_open_questions.append(
                ResolvedQuestion(question=question, answer=answer)
            )
            self.assumptions_from_brief.append(
                f"[Confirmed] {question} → {answer}"
            )
        self.open_questions = []

    def validate_required(self) -> list[str]:
        errors: list[str] = []
        if not self.objectives:
            errors.append("At least one objective is required.")
        if not self.scope_in:
            errors.append("scope_in must contain at least one item.")
        if not self.client_name.strip():
            errors.append("client_name is required.")
        if not self.project_title.strip():
            errors.append("project_title is required.")
        return errors
