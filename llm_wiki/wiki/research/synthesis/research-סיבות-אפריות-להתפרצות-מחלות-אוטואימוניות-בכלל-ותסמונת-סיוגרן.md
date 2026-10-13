---
ai_edit: true
confidence: medium
created: '2026-10-13'
domain:
- research
id: research-סיבות-אפריות-להתפרצות-מחלות-אוטואימוניות-בכלל-ותסמונת-סיוגרן
mocs: []
related: []
share_policy: allowed
source_domain:
- research
sources:
- research_manager/research_12dbf27dc5ac
status: active
tags:
- research_manager
- evidence_synthesis
type: synthesis
updated: '2026-10-13'
---

# Research: סיבות אפריות להתפרצות מחלות אוטואימוניות בכלל ותסמונת סיוגרן

# Final Research Report

## Research Question

סיבות אפריות להתפרצות מחלות אוטואימוניות בכלל ותסמונת סיוגרן בפרט

## Research Method

Phase 1 LangGraph orchestration with mocked medical-source adapters for PubMed, ClinicalTrials.gov, and NCCIH. Workflow: planner -> executor -> evidence_analyst -> critic -> synthesizer -> supervisor.

## Search Sources

- PubMed: papers, reviews, meta-analyses, clinical study publications
- ClinicalTrials.gov: trial phase, recruitment status, outcomes, eligibility, NCT identifiers
- NCCIH: alternative medicine, complementary therapies, mind-body practices, exercise, yoga
- Cochrane Complementary Medicine: systematic reviews of acupuncture, herbal medicine, massage, mind-body therapies, and other CAM interventions
- CAM-Quest: CAM searches by condition, therapy, and study type; useful as a broad historical evidence map
- NIEHS: environmental exposures, pesticides, toxins, gene-environment interaction, autoimmune disease, Parkinson's disease
- NINDS Parkinson's Disease Research: neurodegeneration, dopamine pathways, biomarkers, genetics, mechanisms, disease-modifying treatment research
- NIH Office of Autoimmune Disease Research: autoimmune disease mechanisms, sex differences, immune dysregulation, strategic research priorities
- Michael J. Fox Foundation: Parkinson's biomarkers, genetics, therapeutic pipeline, PPMI, prevention and disease progression research

## Complementary Medicine Domains

- exercise and supervised physical activity
- yoga and breathwork
- mindfulness and meditation
- nutrition and dietary patterns
- supplements and herbal products
- acupuncture and manual therapies
- sleep, stress, and behavioral interventions

## Key Claims

- C1: Phase 1 medical-source mock evidence provides a traceable but low-confidence treatment research synthesis for: סיבות אפריות להתפרצות מחלות אוטואימוניות בכלל ותסמונת סיוגרן בפרט | sources: pubmed_mock_1_review, clinicaltrials_mock_1_trial, nccih_mock_1_integrative, pubmed_mock_2_review, clinicaltrials_mock_2_trial, nccih_mock_2_integrative

## Limitations

- Executor used mocked medical-source adapters only.
- Citation and trial-registry verification are unavailable in Phase 1.
- No live medical literature or trial databases were searched yet.
- This is research organization support, not diagnosis or treatment advice.

## Why Research Stopped

RESOURCE_LIMIT

## References

- study_923da172c9fe: PubMed Mock Review 1 (pubmed_mock_1_review)
- study_3059b074996c: ClinicalTrials.gov Mock Trial 1 (clinicaltrials_mock_1_trial)
- study_3646ce647ece: NCCIH Mock Integrative Health Evidence 1 (nccih_mock_1_integrative)
- study_1c01709665b0: PubMed Mock Review 2 (pubmed_mock_2_review)
- study_1fc0467ff6c6: ClinicalTrials.gov Mock Trial 2 (clinicaltrials_mock_2_trial)
- study_160ec57de3c5: NCCIH Mock Integrative Health Evidence 2 (nccih_mock_2_integrative)

## Provenance & Sources
- `research_manager/research_12dbf27dc5ac`