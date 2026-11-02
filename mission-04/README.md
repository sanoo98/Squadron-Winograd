# Squadron Winograd — Mission 04: Alignment Pipelines & Ethical Steering Core
## Direct Preference Optimization (DPO), Verbosity Regularization & Steering Vector Control

**Starship Operational Unit:** USSE Noosphere Bridge Crew  
**Course:** Conversational AI — Winter Semester 2026/27  
**Galactic Waypoint:** Betelgeuse & Orion Molecular Cloud Complex (SEC-04-ORI, 642 ly from Sol)  
**AURA Core Repair:** Subsystem 04: Plasma Ignition & Ethical Steering Core (+7.1% -> 28.4% Total Integrity)

---

## Mission Overview

Entering the turbulent plasma prominence wake of the red supergiant Betelgeuse (Alpha Orionis), AURA Subsystem 04 experiences severe alignment collapse, alternating between sycophantic hallucinations and catastrophic refusals.

Squadron Winograd engineered and verified the modern alignment and steering pipeline:
1. **Direct Preference Optimization (DPO):** Pure PyTorch mathematical reparameterization bypassing reward models and PPO loops. Vectorized logps gathering with padding mask protection and numerical logsigmoid stability.
2. **Implicit Reward Modeling & Bradley-Terry Calibration:** Closed-form scalar reward extraction $r(x, y) = \beta (\log \pi_\theta - \log \pi_{\text{ref}})$, pairwise ranking accuracy metrics, and reliability calibration curves.
3. **Verbosity Regularization & SimPO:** Diagnosis of length exploitation in preference tuning and implementation of the reference-free SimPO objective with sequence-length normalization and target margin $\gamma = 0.5$.
4. **Inference-Time Activation Steering & Alignment Tax Audit:** Contrast concept vector extraction via representation engineering ($v_{\text{steer}} = \mathbb{E}[h_l(\text{truthful})] - \mathbb{E}[h_l(\text{sycophantic})]$) and runtime residual stream injection ($h_l \leftarrow h_l + \alpha v_{\text{steer}}$), auditing safety win-rates against reasoning retention.

---

## Squadron Officers & Deliverables

| Deliverable | Station Officer | Description |
| :--- | :--- | :--- |
| `01_DPO_Loss_Core.py` | Hassaan Ahmad Khawaja | PyTorch DPO loss implementation with vectorized token gather and gradient isolation test |
| `02_Implicit_Reward_Evaluator.py` | Muhammad Usman Maratib | Implicit reward engine, Bradley-Terry calibration curve, and reliability diagram |
| `03_Length_Bias_and_SimPO.py` | Muhammad Qasim Siddiqui | Length bias correlation diagnostic, SimPO loss implementation, and VRAM benchmark |
| `04_Activation_Steering_and_Audit.py` | Muhammad Qasim Siddiqui | Activation steering vector extraction, PyTorch residual hook, and Alignment Tax audit |
| `ps04_solution.ipynb` | All Officers | Executable Jupyter Notebook demonstrating all alignment pipeline stages |
| `mission-04-doc.md` | All Officers | Official squadron documentation with Mermaid architecture and 4 station sign-offs |
| `mission-04-doc.pdf` | All Officers | Submission PDF document generated locally for Moodle drop-box upload |
| `tests/` | Muhammad Qasim Siddiqui | Automated Pytest unit test suite (`test_ps04.py`) |

---

## Installation & Test Execution

Run unit tests:
```bash
python -m pytest tests -v
```

Execute individual pipeline modules:
```bash
python 01_DPO_Loss_Core.py
python 02_Implicit_Reward_Evaluator.py
python 03_Length_Bias_and_SimPO.py
python 04_Activation_Steering_and_Audit.py
```
