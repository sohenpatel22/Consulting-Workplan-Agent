from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.stakeholder import StakeholderMap
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
            "owner": "Engagement Manager",
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
            "owner": "Business Analyst",
            "estimated_duration": "2 weeks",
            "dependencies": [],
        },
        {
            "level": 2,
            "wbs_code": "1.2",
            "parent_wbs_code": "1.0",
            "wbs_element_title": "Data source inventory",
            "description_scope": "Catalog all data sources",
            "key_deliverable": "Source inventory",
            "owner": "Data Architect",
            "estimated_duration": "3 weeks",
            "dependencies": ["1.1"],
        },
        {
            "level": 1,
            "wbs_code": "2.0",
            "parent_wbs_code": None,
            "wbs_element_title": "Design",
            "description_scope": "Design target architecture",
            "key_deliverable": "Architecture document",
            "owner": "Solution Architect",
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
            "owner": "Solution Architect",
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
            "owner": "Data Engineer",
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
            "owner": "Tech Lead",
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
            "owner": "Data Engineer",
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
            "owner": "Data Engineer",
            "estimated_duration": "4 weeks",
            "dependencies": ["3.1"],
        },
    ],
}

RAID_FIXTURE = {
    "risks": [
        {
            "id": "R1",
            "title": "SME availability",
            "description": "Limited SME time may delay assessment",
            "priority": "High",
            "probability": "High",
            "owner": "Engagement Manager",
            "status": "Open",
            "wbs_links": ["1.1", "1.2"],
            "mitigation": "Pre-book workshops on Tue/Thu",
        },
        {
            "id": "R2",
            "title": "API instability",
            "description": "Salesforce API changes could break ingestion",
            "priority": "Moderate",
            "probability": "Moderate",
            "owner": "Tech Lead",
            "status": "Open",
            "wbs_links": ["3.1"],
            "mitigation": "Version-pin APIs and monitor changelogs",
        },
        {
            "id": "R3",
            "title": "Budget overrun",
            "description": "Azure licensing costs may exceed estimate",
            "priority": "Moderate",
            "probability": "Moderate",
            "owner": "Engagement Manager",
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
            "owner": "Client CIO",
            "status": "Open",
            "wbs_links": ["3.0"],
        },
        {
            "id": "A2",
            "title": "Marketing Cloud ready",
            "description": "SFMC instance provisioned and accessible",
            "priority": "Moderate",
            "owner": "Marketing Ops Lead",
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

STAKEHOLDER_MAP_FIXTURE = {
    "stakeholders": [
        {
            "name": "Elena Vasquez",
            "source": "explicit",
            "rationale": None,
            "department": "Marketing",
            "role_in_project": "CMO",
            "influence_level": "High",
            "interest_level": "High",
            "engagement_strategy": "Manage Closely",
            "key_concerns": "Campaign launch speed, personalization ROI, data subject consent workflows.",
            "communication_frequency": "Bi-weekly",
            "engagement_approach": "Direct consultation",
            "communication_method": "Steering Committee, Monthly Dashboard",
        },
        {
            "name": "Marcus Chen",
            "source": "explicit",
            "rationale": None,
            "department": "IT",
            "role_in_project": "CIO",
            "influence_level": "High",
            "interest_level": "High",
            "engagement_strategy": "Manage Closely",
            "key_concerns": "Technical feasibility, security of Azure tenant, implementation cost under €1.2M.",
            "communication_frequency": "Weekly",
            "engagement_approach": "Collaborative planning",
            "communication_method": "Weekly Progress Call, Architecture Review Board",
        },
        {
            "name": "Priya Sharma",
            "source": "explicit",
            "rationale": None,
            "department": "Data",
            "role_in_project": "Head of Data",
            "influence_level": "Medium",
            "interest_level": "High",
            "engagement_strategy": "Keep Informed",
            "key_concerns": "Data quality, GDPR-compliant consent tracks, team capabilities in Azure Data Factory.",
            "communication_frequency": "Weekly",
            "engagement_approach": "Technical workshops",
            "communication_method": "SME Workshops, Architecture Reviews",
        },
        {
            "name": "James O'Brien",
            "source": "explicit",
            "rationale": None,
            "department": "Marketing Operations",
            "role_in_project": "Marketing Ops Lead",
            "influence_level": "Low",
            "interest_level": "High",
            "engagement_strategy": "Keep Informed",
            "key_concerns": "Audience builder usability, Shopify/SFMC sync speed.",
            "communication_frequency": "Ad-hoc",
            "engagement_approach": "Operational syncs",
            "communication_method": "Day-to-day coordination, Tool training workshops",
        },
        {
            "name": "Legal/Compliance",
            "source": "inferred",
            "rationale": "Required to ensure GDPR compliance of CDP Azure pipelines per constraints",
            "department": "Compliance",
            "role_in_project": "DPO Office",
            "influence_level": "High",
            "interest_level": "Medium",
            "engagement_strategy": "Keep Satisfied",
            "key_concerns": "GDPR compliance, data residency inside EU, consent audit trail.",
            "communication_frequency": "Monthly",
            "engagement_approach": "Milestone reviews",
            "communication_method": "Steering Committee, Legal Sign-off Meetings",
        }
    ]
}

STATUS_REPORT_FIXTURE = {
    "project_name": "Customer Data Platform Modernization",
    "project_manager": "Engagement Manager",
    "date": "2026-06-08",
    "summary": "The CDP modernization initiative officially launched this week with a successful project kickoff. Initial discovery workshops have been scheduled to inventory the legacy data sources. Project is currently on track, within budget, and aligned with timeline objectives.",
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
    "stakeholder_map": STAKEHOLDER_MAP_FIXTURE,
    "status_report": STATUS_REPORT_FIXTURE,
}

FIXTURES: dict = {
    ParsedBrief: PARSED_BRIEF_FIXTURE,
    WBS: WBS_FIXTURE,
    RAIDLog: RAID_FIXTURE,
    StakeholderMap: STAKEHOLDER_MAP_FIXTURE,
    WeeklyStatusReport: STATUS_REPORT_FIXTURE,
}
