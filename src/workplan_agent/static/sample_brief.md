# Client Engagement Brief

**Client:** Northwind Retail Group  
**Project:** Customer Data Platform Modernization  
**Date:** May 2026  
**Prepared by:** Deloitte Consulting

---

## Background

Northwind Retail Group operates 420 stores across 12 countries with fragmented customer data spread across legacy CRM, e-commerce, and loyalty systems. Leadership has approved a 6-month initiative to design and implement a unified Customer Data Platform (CDP) that enables personalized marketing, real-time segmentation, and GDPR-compliant consent management.

The current state creates duplicate customer records, inconsistent segmentation rules, and manual reconciliation processes that delay campaign launches by 2–3 weeks.

## Objectives

1. **Unified customer view** — Consolidate customer profiles from CRM, e-commerce, and loyalty into a single golden record with deduplication rules.
2. **Real-time segmentation** — Enable marketing teams to build and activate audience segments within 24 hours of rule definition.
3. **Compliance readiness** — Implement consent tracking and data subject request workflows aligned with GDPR requirements.
4. **Operational handover** — Transfer platform ownership to Northwind's internal IT team with documented runbooks and training.

## Scope

### In Scope
- Current-state assessment of CRM (Salesforce), e-commerce (Shopify), and loyalty (Custom) data sources
- Target-state CDP architecture design on Azure
- Data ingestion pipelines for batch and near-real-time feeds
- Identity resolution and deduplication rule design
- Marketing audience builder integration (Salesforce Marketing Cloud)
- Consent management module design and implementation
- UAT support and knowledge transfer (2 training sessions)

### Out of Scope
- Legacy system decommissioning
- Store POS integration
- Custom mobile app development
- Ongoing managed services post go-live

## Timeline

| Milestone | Target Date |
|-----------|-------------|
| Project kickoff | June 2, 2026 |
| Current-state assessment complete | July 15, 2026 |
| Target architecture approved | August 1, 2026 |
| MVP ingestion live | September 30, 2026 |
| UAT complete | November 15, 2026 |
| Go-live & handover | December 1, 2026 |

**Total duration:** 6 months (June – December 2026)

## Constraints

- Budget capped at €1.2M including licensing and cloud infrastructure
- Must use existing Azure tenant; no new cloud provider
- All PII must remain within EU data residency boundaries
- Northwind IT team has limited Azure Data Factory experience — training is essential
- Marketing team availability for workshops limited to Tuesdays and Thursdays

## Key Stakeholders

| Name | Role | Interest |
|------|------|----------|
| Elena Vasquez | CMO | Campaign speed, personalization ROI |
| Marcus Chen | CIO | Technical feasibility, security, cost |
| Priya Sharma | Head of Data | Data quality, governance, team capability |
| James O'Brien | Marketing Ops Lead | Day-to-day segment building, tool usability |
| Legal/Compliance | DPO Office | GDPR compliance, audit trail |

## Assumptions

- Salesforce and Shopify APIs remain stable during the engagement
- Northwind will provide dedicated SMEs for 4 hours/week per source system
- Azure Databricks and Data Factory licenses are procured by client before build phase
- Marketing Cloud instance is already provisioned and accessible

## Open Items

- Final decision on identity resolution vendor (internal rules vs. third-party MDM)
- Whether loyalty system migration timeline affects CDP go-live scope
