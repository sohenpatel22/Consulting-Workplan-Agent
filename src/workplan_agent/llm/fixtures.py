from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
from workplan_agent.models.status_report import WeeklyStatusReport

PARSED_BRIEF_FIXTURE = {
    "client_name": "Northwind Retail Group",
    "project_title": "Customer Data Platform Modernization",
    "background": "Fragmented customer data across legacy systems.",
    "objectives": [
        {
            "id": "O1",
            "description": "Unified customer view",
            "success_criteria": "Single golden record with deduplication",
        },
        {
            "id": "O2",
            "description": "Real-time segmentation",
            "success_criteria": "Segments activated within 24 hours",
        },
    ],
    "scope_in": [
        "Current-state assessment of CRM, e-commerce, loyalty",
        "Target-state CDP architecture on Azure",
        "Data ingestion pipelines",
    ],
    "scope_out": ["Legacy decommissioning", "POS integration"],
    "constraints": [
        {"type": "Budget", "description": "Capped at €1.2M"},
        {"type": "Compliance", "description": "PII within EU boundaries"},
    ],
    "timeline": {
        "start": "June 2, 2026",
        "end": "December 1, 2026",
        "milestones": ["Kickoff", "Architecture approved", "Go-live"],
    },
    "stakeholders": [
        {"name": "Elena Vasquez", "role": "CMO", "interest": "Campaign speed"},
        {"name": "Marcus Chen", "role": "CIO", "interest": "Security and cost"},
    ],
    "assumptions_from_brief": ["Salesforce APIs remain stable"],
    "open_questions": ["Identity resolution vendor decision pending"],
    "planner_confirmations": [
        {
            "question": "Identity resolution vendor decision pending",
            "suggested_answers": [
                "Standardize on the incumbent identity platform",
                "Run a short vendor bake-off before architecture sign-off",
                "Defer vendor selection — document as a RAID decision",
            ],
            "brief_quotes": [
                "Identity resolution vendor decision pending",
            ],
            "derivation_rationale": (
                "The brief flags the identity vendor as undecided but does not say "
                "whether to standardize now, run a bake-off, or defer — we need that "
                "choice before architecture and build tasks are scheduled."
            ),
        }
    ],
}

WBS_FIXTURE = {
    "work_packages": [
        {
            "level": 1,
            "wbs_code": "1.0",
            "parent_wbs_code": None,
            "wbs_element_title": "Discovery",
            "description_scope": "Assess current state",
            "key_deliverable": "Assessment report",
            "owner": "Deloitte Delivery Lead",
            "estimated_duration": "6 weeks",
            "dependencies": [],
        },
        {
            "level": 2,
            "wbs_code": "1.1",
            "parent_wbs_code": "1.0",
            "wbs_element_title": "Stakeholder interviews",
            "description_scope": "Interview key stakeholders",
            "key_deliverable": "Interview notes",
            "owner": "Deloitte Delivery Lead",
            "estimated_duration": "2 weeks",
            "dependencies": [],
        },
        {
            "level": 3,
            "wbs_code": "1.1.1",
            "parent_wbs_code": "1.1",
            "wbs_element_title": "Executive stakeholder sessions",
            "description_scope": "Interview CIO and CMO",
            "key_deliverable": "Executive interview notes",
            "owner": "Deloitte Delivery Lead",
            "estimated_duration": "3 days",
            "dependencies": [],
        },
        {
            "level": 2,
            "wbs_code": "1.2",
            "parent_wbs_code": "1.0",
            "wbs_element_title": "Data source inventory",
            "description_scope": "Catalog all data sources",
            "key_deliverable": "Source inventory",
            "owner": "Data Engineering Lead",
            "estimated_duration": "3 weeks",
            "dependencies": ["1.1"],
        },
        {
            "level": 3,
            "wbs_code": "1.2.1",
            "parent_wbs_code": "1.2",
            "wbs_element_title": "CRM source profiling",
            "description_scope": "Profile Salesforce CRM volumes",
            "key_deliverable": "CRM profile report",
            "owner": "Data Engineering Lead",
            "estimated_duration": "1 week",
            "dependencies": ["1.1.1"],
        },
        {
            "level": 1,
            "wbs_code": "2.0",
            "parent_wbs_code": None,
            "wbs_element_title": "Design",
            "description_scope": "Design target architecture",
            "key_deliverable": "Architecture document",
            "owner": "Client CIO",
            "estimated_duration": "4 weeks",
            "dependencies": ["1.0"],
        },
        {
            "level": 2,
            "wbs_code": "2.1",
            "parent_wbs_code": "2.0",
            "wbs_element_title": "Target architecture",
            "description_scope": "Define CDP architecture",
            "key_deliverable": "Architecture diagram",
            "owner": "Client CIO",
            "estimated_duration": "2 weeks",
            "dependencies": [],
        },
        {
            "level": 2,
            "wbs_code": "2.2",
            "parent_wbs_code": "2.0",
            "wbs_element_title": "Integration design",
            "description_scope": "Design ingestion pipelines",
            "key_deliverable": "Integration spec",
            "owner": "Data Engineering Lead",
            "estimated_duration": "2 weeks",
            "dependencies": ["2.1"],
        },
        {
            "level": 1,
            "wbs_code": "3.0",
            "parent_wbs_code": None,
            "wbs_element_title": "Build",
            "description_scope": "Implement CDP components",
            "key_deliverable": "Working CDP MVP",
            "owner": "Deloitte Delivery Lead",
            "estimated_duration": "10 weeks",
            "dependencies": ["2.0"],
        },
        {
            "level": 2,
            "wbs_code": "3.1",
            "parent_wbs_code": "3.0",
            "wbs_element_title": "Ingestion pipelines",
            "description_scope": "Build batch and streaming feeds",
            "key_deliverable": "Pipeline deployment",
            "owner": "Data Engineering Lead",
            "estimated_duration": "5 weeks",
            "dependencies": [],
        },
        {
            "level": 2,
            "wbs_code": "3.2",
            "parent_wbs_code": "3.0",
            "wbs_element_title": "Identity resolution",
            "description_scope": "Implement dedup rules",
            "key_deliverable": "Identity module",
            "owner": "Data Engineering Lead",
            "estimated_duration": "4 weeks",
            "dependencies": ["3.1"],
            "from_confirmed_answer": True,
        },
    ],
}

RAID_FIXTURE = {
    "risks": [
        {
            "id": "R1",
            "title": "SME availability",
            "description": "Limited SME time may delay assessment",
            "probability": "High",
            "impact": "Moderate",
            "risk_rating": "High",
            "risk_appetite": "Moderate",
            "priority": "Monitor closely",
            "owner": "Deloitte Delivery Lead",
            "status": "Open",
            "wbs_links": ["1.1", "1.2"],
            "mitigation": "Pre-book workshops on Tue/Thu",
        },
        {
            "id": "R2",
            "title": "API instability",
            "description": "Salesforce API changes could break ingestion",
            "probability": "Moderate",
            "impact": "Low",
            "risk_rating": "Moderate",
            "risk_appetite": "Moderate",
            "priority": "Monitor",
            "owner": "Data Engineering Lead",
            "status": "Open",
            "wbs_links": ["3.1"],
            "mitigation": "Version-pin APIs and monitor changelogs",
        },
        {
            "id": "R3",
            "title": "Budget overrun",
            "description": "Azure licensing costs may exceed estimate",
            "probability": "Low",
            "impact": "High",
            "risk_rating": "Moderate",
            "risk_appetite": "Moderate",
            "priority": "Stay informed",
            "owner": "Deloitte Delivery Lead",
            "status": "Open",
            "wbs_links": ["3.0"],
            "mitigation": "Weekly cost tracking with client CIO",
        },
    ],
    "actions": [
        {
            "id": "A1",
            "title": "Azure licenses procured",
            "description": "Client procures Databricks/ADF before build",
            "priority": "High",
            "owner": "Deloitte Delivery Lead",
            "status": "Open",
            "wbs_links": ["3.0"],
        },
        {
            "id": "A2",
            "title": "Marketing Cloud ready",
            "description": "SFMC instance provisioned and accessible",
            "priority": "Moderate",
            "owner": "Data Engineering Lead",
            "status": "Open",
            "wbs_links": ["2.2"],
        },
    ],
    "issues": [],
    "decisions": [
        {
            "id": "D1",
            "title": "Architecture approval",
            "description_justification": "Build depends on approved architecture",
            "priority": "High",
            "owner": "CIO",
            "resolution": "",
        },
    ],
}

RACI_MATRIX_FIXTURE = {
    "roles": [
        "Deloitte Delivery Lead",
        "Data Engineering Lead",
        "Client CIO",
    ],
    "rows": [
        {
            "wbs_code": "1.1",
            "activity": "Stakeholder interviews",
            "assignments": {
                "Deloitte Delivery Lead": "R",
                "Data Engineering Lead": "C",
                "Client CIO": "A",
            },
        },
        {
            "wbs_code": "1.1.1",
            "activity": "Executive stakeholder sessions",
            "assignments": {
                "Deloitte Delivery Lead": "R",
                "Data Engineering Lead": "I",
                "Client CIO": "A",
            },
        },
        {
            "wbs_code": "1.2",
            "activity": "Data source inventory",
            "assignments": {
                "Deloitte Delivery Lead": "A",
                "Data Engineering Lead": "R",
                "Client CIO": "C",
            },
        },
        {
            "wbs_code": "1.2.1",
            "activity": "CRM source profiling",
            "assignments": {
                "Deloitte Delivery Lead": "A",
                "Data Engineering Lead": "R",
                "Client CIO": "C",
            },
        },
        {
            "wbs_code": "2.1",
            "activity": "Target architecture",
            "assignments": {
                "Deloitte Delivery Lead": "C",
                "Data Engineering Lead": "I",
                "Client CIO": "A",
            },
        },
        {
            "wbs_code": "2.2",
            "activity": "Integration design",
            "assignments": {
                "Deloitte Delivery Lead": "A",
                "Data Engineering Lead": "R",
                "Client CIO": "C",
            },
        },
        {
            "wbs_code": "3.1",
            "activity": "Ingestion pipelines",
            "assignments": {
                "Deloitte Delivery Lead": "A",
                "Data Engineering Lead": "R",
                "Client CIO": "C",
            },
        },
        {
            "wbs_code": "3.2",
            "activity": "Identity resolution",
            "assignments": {
                "Deloitte Delivery Lead": "A",
                "Data Engineering Lead": "R",
                "Client CIO": "I",
            },
        },
    ],
}

STATUS_REPORT_FIXTURE = {
    "project_name": "Customer Data Platform Modernization",
    "project_manager": "Engagement Manager",
    "date": "2026-06-08",
    "summary": [
        "CDP modernization initiative launched with a successful project kickoff.",
        "Initial discovery workshops scheduled to inventory legacy data sources.",
        "Project is on track, within budget, and aligned with timeline objectives."
    ],
    "new_initiatives": [
        "Project kickoff meeting completed with all core stakeholders.",
        "Detailed project charter and communication plan signed off."
    ],
    "blockers": [
        "SME availability due to conflicting schedules"
    ],
    "risks": [
        "SME availability may delay assessment (R1)"
    ],
    "milestones": [
        {"name": "Kickoff", "target_date": "June 2, 2026", "actual_date": "June 2, 2026", "status": "Completed"},
        {"name": "Architecture approved", "target_date": "August 1, 2026", "actual_date": None, "status": "Not Started"},
        {"name": "Go-live", "target_date": "December 1, 2026", "actual_date": None, "status": "Not Started"}
    ],
    "supporting_links": [
        "https://sharepoint.northwind.com/cdp-charter.pdf"
    ]
}

REVISION_FIXTURE = {
    "wbs": WBS_FIXTURE,
    "raid": RAID_FIXTURE,
    "raci_matrix": RACI_MATRIX_FIXTURE,
    "status_report": STATUS_REPORT_FIXTURE,
}

FIXTURES: dict = {
    ParsedBrief: PARSED_BRIEF_FIXTURE,
    WBS: WBS_FIXTURE,
    RAIDLog: RAID_FIXTURE,
    RaciMatrix: RACI_MATRIX_FIXTURE,
    WeeklyStatusReport: STATUS_REPORT_FIXTURE,
}
