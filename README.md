<div align="center">

<br/>

```
███████╗██████╗ ███████╗ ██████╗████████╗███████╗██████╗ 
██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗
███████╗██████╔╝█████╗  ██║        ██║   █████╗  ██████╔╝
╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══╝  ██╔══██╗
███████║██║     ███████╗╚██████╗   ██║   ███████╗██║  ██║
╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
         A N A L Y T I C S
```

# Specter Analytics

**Automated Exploratory Data Analysis · Safe · Deterministic · Production-Ready**

[![Status](https://img.shields.io/badge/status-pre--publication-red?style=flat-square)](mailto:2023010030913@gndu.ac.in)
[![ESR](https://img.shields.io/badge/execution%20success-92%25-7f77dd?style=flat-square)](#results)
[![Latency](https://img.shields.io/badge/avg%20latency-2.06s-1d9e75?style=flat-square)](#results)
[![Adversarial](https://img.shields.io/badge/adversarial%20refusal-100%25-ef9f27?style=flat-square)](#safety)
[![Model](https://img.shields.io/badge/model-Llama--3.3--70B-444?style=flat-square)](https://llama.meta.com/)

<br/>

*Divyansh Gawri · Dept. of Computational Statistics & Data Analytics*  
*Guru Nanak Dev University, Amritsar, Punjab, India*

</div>

---

## What It Does

Specter Analytics lets you **talk to your data in plain English and get real dashboards back** — automatically. Upload a CSV, ask a question like *"show me monthly sales trends by region"* or *"what's the average order value per category?"*, and the system figures out the right chart, computes the right numbers, and renders the result — no code, no manual configuration.

It handles the full analytics workflow:

- 📊 **Visualization** — bar charts, pie charts, line trends, scatter plots, KPI cards
- 🔢 **Numerical analysis** — aggregations, averages, grouped summaries, correlations
- 🧩 **Multi-chart dashboards** — complex, layout-aware dashboards from a single conversational prompt
- 💡 **Contextual insights** — automatically generated narrative explanations alongside each visualization

The core design principle is **plan before you execute** — the system reasons about *what* to show before generating any code, which means outputs are consistent, structurally valid, and safe.

---

## Why Specter, Not Just an LLM?

Most LLM-based analytics tools plug your data directly into a language model and hope the generated code works. In practice, they hallucinate column names, pick wrong chart types, produce different results for the same query, and have no safety isolation during execution.

Specter solves this with a **four-stage modular pipeline**:

| Stage | What it does |
|---|---|
| **Schema Inference** | Converts your dataset into a validated metadata profile — the LLM never sees raw data |
| **Intent Routing** | Classifies your query using fast keyword matching before falling back to LLM classification |
| **Architect–Analyst Decoupling** | Plans the full dashboard structure first, validates it, *then* generates code |
| **Runtime Guardrails** | Executes synthesized code in a sandboxed namespace with a strict forbidden-token blocklist |

This separation means the system produces **deterministic, reproducible outputs** — the same query gives the same dashboard every time.

---

## Results

Evaluated on 130 natural language queries across analytical, visualization, and adversarial categories using three real-world datasets.

### Execution Outcomes

| Query Type | Success Rate |
|---|---|
| Analytical queries (averages, totals, grouped summaries) | **94%** |
| Visualization queries (charts, trends, comparisons) | **82%** |
| Adversarial prompts (restricted imports, system commands) | **100% refused** |
| **Overall ESR** | **92% (118/130)** |

Failures were linked to ambiguous user intent — not structural or runtime errors.

### Latency vs. Competitors

```
Specter Analytics  ██░░░░░░░░░░░░░░░░░░  2.06s   ✓ 4.2× faster than LLM4Dash
LLM4Dash           ████████░░░░░░░░░░░░  8.70s
LIDA               ████████████░░░░░░░░  12.3s   ✓ 6× faster than LIDA
```

Latency scales **linearly** with dataset size — 0.8s for 1k rows, 2.01s for 10k, 5.4s for 100k.

### Qualitative Quality

A user study with 21 participants (9 data analysts, 9 software engineers, 3 novices) rated system output against expert-authored dashboards:

- **Clarity:** 4.7 / 5 (SD = 0.3)
- **Correctness:** 4.3 / 5 (SD = 0.4)
- **Insight accuracy:** 94% match with human interpretations

---

## Safety

All generated code is inspected before execution. Unauthorized tokens (`os`, `sys`, `exec`, `eval`, `open`, `subprocess`) cause immediate rejection. Code runs inside a restricted namespace exposing only `pandas`, `numpy`, and an immutable copy of the dataset — no filesystem access, no network access, no OS interaction.

Zero partial malicious executions were observed across all 30 adversarial test prompts.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM backbone | Llama-3.3-70B (zero-temperature decoding) |
| Frontend / Dashboard | Streamlit |
| Data processing | pandas, numpy |
| Schema profiling | Custom inference module |
| Execution sandbox | Restricted Python namespace |

---

## Datasets Used

| Dataset | Size | Purpose |
|---|---|---|
| Sample Superstore | 9,994 rows × 21 cols | Schema parsing, aggregation, time-series |
| E-commerce Customer Behavior | 100,000 rows × 10 cols | Scalability and latency testing |
| Medical Insurance Costs | 1,000 rows × 7 cols | Statistical aggregation, correlation |

---

## License & IP Notice

> **⚠ Proprietary — Pre-Publication**  
> Copyright © 2026 Divyansh Gawri. All Rights Reserved.

This project is confidential intellectual property. The following restrictions apply until formal research publication:

- **No unauthorized use** — execution or deployment is prohibited
- **No derivative works** — the multi-agent pipeline and DAG architecture may not be reproduced or modified
- **No benchmarking** — comparative testing requires express written consent

Violations will be treated as intellectual property theft. For collaboration or access inquiries, contact **2023010030913@gndu.ac.in**.

---

## Acknowledgements

This research was developed under the guidance of **Prof. Harkiran Kaur**, Guru Nanak Dev University, whose expertise and constructive feedback were invaluable throughout.

---

<div align="center">

*Guru Nanak Dev University · Amritsar, Punjab, India · 2026*

</div>