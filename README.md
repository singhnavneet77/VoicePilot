# VANI Experiment Center — Agent A/B Testing & Auto-Rollout

A hackathon-ready implementation for **Voice AI Hackathon 2.0 — PS05: Agent A/B Testing & Auto-Rollout**.

## What this project demonstrates

- Versioned A/B experiment configuration
- Random + **sticky** lead assignment using SHA-256 hashing
- Configurable traffic split
- Primary metric: `meeting_fixed`
- Secondary metric: `call_duration_sec`
- Two-proportion statistical test
- Pre-declared decision rules
- Conservative repeated-look correction (Bonferroni alpha spending)
- Winner / inconclusive / early-stop decisions
- Automatic promotion of the winning variant
- Automatic early stop of a clearly worse treatment
- Decision audit log
- Configured-vs-achieved split evidence
- Interactive Streamlit dashboard
- Built-in traffic simulator with three judge-ready scenarios
- CSV upload/replay mode for organizer data
- Unit tests for assignment and statistics

> Important: the built-in simulator is a demo/replay mechanism, not proof of real-world causal lift. For real organizer data, use the same engine with observed outcomes and clearly document the replay assumptions.

## Project structure

```text
vani_ab_rollout/
├── app/
│   └── streamlit_app.py
├── engine/
│   ├── __init__.py
│   ├── experiment.py
│   ├── simulator.py
│   └── stats.py
├── tests/
│   ├── test_assignment.py
│   └── test_stats.py
├── data/
│   └── README.md
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

## 1. Install

Python 3.10+ recommended.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run the app

```bash
streamlit run app/streamlit_app.py
```

Open the local URL shown by Streamlit, normally:

```text
http://localhost:8501
```

## 3. Judge-ready demo

Open the **Demo Scenarios** tab.

Run:

1. **B wins** — treatment has a meaningful improvement and becomes the winner.
2. **B clearly worse** — treatment is stopped early and traffic returns to A.
3. **Inconclusive** — the experiment cannot establish a winner.

The UI also shows:

- configured traffic
- achieved traffic
- sample size
- meeting-fixed rate
- lift
- confidence interval
- p-value
- current decision
- audit trail

## 4. Using organizer CSV data

The app accepts a CSV with at least:

```text
lead_id,variant,meeting_fixed,call_duration_sec,timestamp
```

Example:

```csv
lead_id,variant,meeting_fixed,call_duration_sec,timestamp
L001,A,1,48,2026-10-08T10:00:00
L002,B,0,71,2026-10-08T10:01:00
```

`meeting_fixed` should be 0/1.

For observed historical data, do **not** claim that a historical replay proves causal impact. Use it as replay evidence and state the limitation.

## 5. Recommended hackathon story

### Problem

Prompt changes currently rely on judgement. A bad change can affect many calls before anyone notices.

### Solution

```text
Prompt A / Prompt B
        ↓
Sticky traffic router
        ↓
Outcome tracking
        ↓
Statistical decision engine
        ↓
 ┌───────────────┬────────────────┐
 │               │                │
 B wins       Inconclusive      B worse
 │               │                │
Promote B      Keep testing     Stop B
                                 ↓
                              Return to A
```

### Why it stands out

The demo is not just "A/B testing". It visibly proves all three business outcomes:

- B wins → promote
- B is dangerous → stop early
- evidence is weak → do not pretend there is a winner

## 6. Statistical policy

The engine uses a two-sided two-proportion z-test for the binary primary metric.

Because the hackathon requires repeated checks to be handled carefully, the demo uses:

```text
family-wise alpha = 0.05
maximum planned looks = 5
per-look alpha = 0.01
```

A winner is declared only when:

```text
p < 0.01
AND
95% CI for (B - A) is entirely above 0
AND
B has a higher point estimate
```

A treatment is stopped early when:

```text
p < 0.01
AND
95% CI for (B - A) is entirely below 0
```

Otherwise the result remains **inconclusive**.

This is intentionally conservative and easy to defend in a short presentation.

## 7. Suggested 3-minute demo

**0:00–0:25 — Setup**

"Control A is our current prompt. B is the candidate prompt. We send 10% sticky traffic to B."

**0:25–1:00 — B wins**

Show:

```text
A = 8.1%
B = 10.0%
Lift = +23.5%
p < 0.01
Decision = PROMOTE B
```

Click Promote.

**1:00–1:40 — B is dangerous**

Switch scenario.

Show:

```text
A = 8.1%
B = 5.0%
Decision = STOP B EARLY
```

Show traffic returned to A.

**1:40–2:15 — Inconclusive**

Show a small/noisy difference.

```text
A = 8.1%
B = 8.4%
Decision = INCONCLUSIVE
```

Say:

> "The system refuses to ship a change when evidence is insufficient."

**2:15–2:45 — Split evidence**

Show:

```text
Configured: 90 / 10
Achieved:   89.8 / 10.2
```

and sticky assignment verification.

**2:45–3:00 — Close**

> "VANI Experiment Center turns prompt changes from judgement-based releases into evidence-based, reversible decisions."

## 8. Testing

```bash
pytest -q
```

## 9. Docker

```bash
docker build -t vani-ab-rollout .
docker run -p 8501:8501 vani-ab-rollout
```

Then open:

```text
http://localhost:8501
```

## 10. What to improve if organizers provide live infrastructure

- Replace simulator with a real traffic router.
- Persist experiments in Postgres.
- Add Redis for assignment cache.
- Add authentication/RBAC.
- Add real prompt execution.
- Add sequential-testing method such as alpha spending or a Bayesian decision policy.
- Add production monitoring and rollback safeguards.

## 11. Honest limitation

The simulator creates controlled outcomes so the three decision paths can be demonstrated reliably. It must not be presented as real-world evidence. With organizer data, report exactly what was observed/replayed and separate simulation results from historical results.
