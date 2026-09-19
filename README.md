# CareSight: Explainable Clinical Health Risk Screening and Patient Triage Platform

## Project Overview
**CareSight** is a full-stack clinical intake and health risk screening platform designed for primary care clinics and community health centers. Traditional medical risk calculators often function as "black boxes," providing static probabilities without actionable context. 

CareSight bridges this gap by combining standardized physiological risk scoring with **transparent, factor-level feature attributions** (explainable AI). The platform enables clinical staff to conduct structured patient intakes, assess multi-disease risk profiles, view longitudinal health trajectories across visits, and export audit-logged clinical summary reports.


---

##  Team Information — **Edge Case Devs**

| Full Name | Lakehead Email Address | GitHub Profile |
| :--- | :--- | :--- |
| **Krish Bista** | `kbista@lakeheadu.ca` | [@krish-bista](https://github.com/krish-bista) |
| **Nate Smith** | `Lnsmith1@lakeheadu.ca` | [@n85mith](https://github.com/n85mith) |
| **Clara Kress** | `cjkress@lakeheadu.ca` | _Profile Link_ |
| **Nischal Shrestha** | `nshrest2@lakeheadu.ca` | _Profile Link_ |

---

##  Primary Users & Core Capabilities

* **Triage Nurse / Medical Assistant**:
  * Input patient demographics, vitals, and lifestyle markers into standardized digital intake forms.
  * Initiate multi-condition risk assessments and view historical screening sessions.
* **Clinician / Physician**:
  * Inspect interpretable factor-attribution risk breakdowns to understand underlying risk drivers.
  * Record clinical notes, apply diagnostic overrides, and export formatted assessment summaries.
* **Clinic Administrator**:
  * Manage staff credentials, assign role-based access control (RBAC), and monitor immutable compliance audit logs.

---

##  Preliminary Technology Stack

* **Frontend**: React, TypeScript, Tailwind CSS
* **Backend API**: Python (FastAPI)
* **Risk & Explainability Engine**: Scikit-learn, ONNX Runtime, SHAP
* **Database & ORM**: PostgreSQL, SQLAlchemy, Alembic (schema migrations)
* **DevOps & QA**: Docker, PyTest, Jest, GitHub Actions (CI automated testing & linting)

---

