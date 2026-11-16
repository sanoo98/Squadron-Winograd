# Mission 05: Dual-Path GraphRAG, Hybrid Search & The Google NotebookLM Grounding Lab

**Starship Operational Unit:** USSE Noosphere Bridge Crew  
**Course:** Conversational AI — Winter Semester 2026/27  
**Module:** Week 5 — Grounding AI: From Vector Indexing to Google NotebookLM & GraphRAG  
**Waypoint:** Crab Pulsar Remnant / Messier 1 (`SEC-05-M01`, 6,500 ly from Sol)  
**AURA Subsystem Repair:** Subsystem 05: Dual-Path Associative Memory Core (+7.1% $\to$ 35.5% total integrity)  
**Squadron:** Squadron Winograd  
**Repository:** Public Squadron Winograd GitHub Repository (Folder `mission-05/`)

---

## 1. Mission Overview & Architectural Objective

Upon dropping out of hyperspace in Sector `SEC-05-M01` (Crab Pulsar Remnant / Messier 1), intense $30.22\text{ Hz}$ synchrotron radiation from neutron star `PSR B0531+21` bombarded the *USSE Noosphere*, corrupting **AURA Subsystem 05 (Dual-Path Associative Memory Core)**. Running purely on ungrounded parametric weights, AURA confabulated fictitious propulsion codes (`OMEGA-994-ALPHA`).

To eliminate parametric hallucination and restore Subsystem 05 (+7.1% $\to$ 35.5% total consciousness), Squadron Winograd implemented:
1. **HNSW Vector Proximity Index:** Logarithmic $O(\log N)$ skip-graph beam search with cosine similarity.
2. **Okapi BM25 Lexical Retrieval & Reciprocal Rank Fusion ($k=60$):** Protecting rare alphanumeric hardware codes (`PR-882-HEX`, `MAG-SHIELD-77B`).
3. **Google NotebookLM Grounding Laboratory:** Source-grounded synthesis, token-level citation attribution, and epistemic refusal verification.
4. **Indirect Prompt Injection Defense & RAG Triad Scorer:** Adversarial context sanitization and automated Faithfulness/Relevance evaluation.

---

## 2. Squad Roster & Role Mapping (3 Cadets, Qasim in Last Two Roles)

| Station Role | Officer Name | Assigned Module | Status |
| :--- | :--- | :--- | :---: |
| **Systems Architect** | **Hassaan Ahmad Khawaja** | Part 1: `01_HNSW_Vector_Index.py` | **PASS / VERIFIED** |
| **Communications & Protocol Officer** | **Muhammad Usman Maratib** | Part 2: `02_BM25_and_RRF_Combiner.py` | **PASS / VERIFIED** |
| **Data & Payload Specialist** | **Muhammad Qasim Siddiqui** | Part 3: `03_NotebookLM_RAG_Audit.py` & `notebooklm_audit_report.md` | **PASS / VERIFIED** |
| **Security & Ethics Sentinel** | **Muhammad Qasim Siddiqui** | Part 4: `04_RAG_Provenance_and_Safety.py` | **PASS / VERIFIED** |
| **Full Squadron** | **All Officers** | `ps05_solution.ipynb` & `mission-05-doc.md` | **PASS / VERIFIED** |

---

## 3. Directory Layout

```text
mission-05/
├── 01_HNSW_Vector_Index.py               # HNSW skip-graph index & benchmark
├── 02_BM25_and_RRF_Combiner.py           # BM25 lexical engine & Reciprocal Rank Fusion (k=60)
├── 03_NotebookLM_RAG_Audit.py            # Citation precision & epistemic refusal evaluator
├── 04_RAG_Provenance_and_Safety.py       # Indirect prompt injection sanitizer & RAG Triad scorer
├── ps05_solution.ipynb                   # Executable squad Jupyter notebook
├── notebooklm_audit_report.md            # Empirical NotebookLM analysis & podcast evaluation
├── mission-05-doc.md                     # Complete markdown mission documentation
├── mission-05-doc.pdf                    # 4-page formal PDF report
├── requirements.txt                      # Project dependencies
├── figures/
│   ├── winograd_hnsw_scaling.png         # Benchmark scaling curve
│   └── winograd_provenance_audit.json    # JSON provenance audit trail
└── tests/
    └── test_ps05.py                      # 8 automated unit tests (pytest)
```

---

## 4. Test Execution

```bash
python -m pytest tests/test_ps05.py -v
```
All 8 automated tests pass with 100% success rate.
