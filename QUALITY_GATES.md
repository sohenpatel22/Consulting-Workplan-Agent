# Consulting Workplan Agent - Quality Gates & Failure Modes

This document defines the **Quality Gates** checklist ("what a human must verify") and analyzes the primary **Failure Modes** and mitigation strategies for the multi-agent generation pipeline.

---

## 1. Quality Gates Checklist

The following checklists must be reviewed and signed off by an Engagement Manager before any deliverables are shared with clients.

### 📋 A. Work Breakdown Structure (WBS) Quality Gate
> [!NOTE]
> Ensure the WBS aligns with the Deloitte consulting WBS standards in structure and style.
* [ ] **Hierarchical Code Validity**: Check that every level-2 package has a parent code that matches a level-1 package (e.g. `1.1` under `1.0`).
* [ ] **Duration Realism**: Confirm task durations are realistic based on brief constraints (e.g. a discovery phase should not take 6 months for a 6-month project).
* [ ] **Resource/Owner Roles**: Confirm every work package has a clear owner assigned to standard consulting roles (e.g., Engagement Manager, Solution Architect, Data Engineer).
* [ ] **Deliverable Completeness**: Confirm that every leaf work package specifies concrete, checkable deliverables rather than vague activities.
* [ ] **Dependency Alignment**: Ensure that dependencies do not create logical loops and correspond to the project timeline.

### 📋 B. RAID Log Quality Gate
> [!IMPORTANT]
> Verify that risks are distinguished from issues, and decisions are traced back to the brief/WBS.
* [ ] **Risk vs. Issue Classification**: Verify that items in the Risks section are future uncertainties (with probability < 100%), and active problems are classified as Issues.
* [ ] **WBS Traceability**: Confirm that every Risk entry lists the WBS codes of affected work packages.
* [ ] **Owner Assignment**: Verify that all Risks, Actions, and Issues have an active owner assigned (rather than being unassigned or marked as "TBD").
* [ ] **Mitigation Actionability**: Ensure risk mitigations are specific, actionable steps (e.g. "Pre-book workshops") rather than generic advice (e.g. "Manage stakeholder closely").

### 📋 C. Stakeholder Map Quality Gate
> [!TIP]
> Use the Influence/Interest matrix to validate the engagement strategies.
* [ ] **Influence/Interest Mapping**: Check if key decision-makers (e.g. CIO, CMO) are marked as High Influence / High Interest.
* [ ] **Strategy Suitability**: Confirm that engagement strategies align with the power/influence levels:
  * High Power, High Interest $\rightarrow$ **Manage Closely**
  * High Power, Low Interest $\rightarrow$ **Keep Satisfied**
  * Low Power, High Interest $\rightarrow$ **Keep Informed**
  * Low Power, Low Interest $\rightarrow$ **Monitor**
* [ ] **Communication Completeness**: Ensure a channel and frequency (e.g., Weekly, Bi-weekly) are defined for all key stakeholders.

### 📋 D. Weekly Status Report Quality Gate
* [ ] **RAG Status Justification**: Confirm the overall project RAG status (Green, Amber, Red) matches the risk log (e.g. Red if a critical high-probability risk is unmitigated).
* [ ] **Milestone Synchronization**: Confirm the listed milestones, target dates, and statuses match the timeline in the parsed brief and WBS.
* [ ] **Activity Alignment**: Verify that planned next-week activities directly map to upcoming work packages in the WBS.

---

## 2. Failure Modes and Mitigation Strategies

Below is a diagnostic guide of potential agent failure modes, how they manifest, and how they are mitigated.

| ID | Failure Mode | Manifestation / Symptom | Mitigation / Solution |
|----|--------------|-------------------------|-----------------------|
| **FM-1** | WBS Parent Code Mismatch | A level-2 package lists a non-existent parent code (e.g. `1.1` points to parent `3.0`). | **Automated Schema Gate**: Parser schema validates code prefix matching. **Human Gate**: Highlight codes in the Web UI. |
| **FM-2** | Orphaned RAID Mappings | Risks have empty `wbs_links` or link to non-existent packages. | **Automated Validation**: Validator checks all link mappings against WBS keys. |
| **FM-3** | Duration Overrun | Sum of phase durations exceeds the client's hard timeline constraint. | **Prompt Instruction**: Injected constraints from parsed brief enforce duration ceilings. |
| **FM-4** | Misaligned RAG Status | Overall project status is marked "Green" despite critical open Issues. | **Agent Revision**: Revision loop allows correcting RAG status via specific reviewer feedback. |
| **FM-5** | Stakeholder Omission | CMO or key project sponsor mentioned in brief is omitted from the stakeholder map. | **Prompt Gate**: Cross-check mapped stakeholders against the parsed brief stakeholder collection. |

---

## 3. How to Use the Quality Gates in the Pipeline
1. During generation, the agent automatically executes check validators.
2. Review the **Quality Gates** tab in the Web UI before final session approval.
3. Check the checklist items generated in the `quality_gates.md` artifact in your output directory.
