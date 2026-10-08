from dataclasses import dataclass
import numpy as np
import pandas as pd

from .experiment import assign_variant


@dataclass
class Scenario:
    name: str
    description: str
    a_rate: float
    b_rate: float
    a_duration: float
    b_duration: float
    seed: int


SCENARIOS = {
    "B wins": Scenario(
        "B wins",
        "Treatment improves meeting-fixed rate while keeping duration reasonable.",
        0.081,
        0.101,
        58,
        54,
        42,
    ),
    "B clearly worse": Scenario(
        "B clearly worse",
        "Treatment harms the primary metric and should be stopped early.",
        0.081,
        0.050,
        58,
        66,
        43,
    ),
    "Inconclusive": Scenario(
        "Inconclusive",
        "Treatment is close to control; evidence should not justify shipping it.",
        0.081,
        0.084,
        58,
        57,
        44,
    ),
}


def simulate_calls(
    scenario: Scenario,
    n: int = 12000,
    split_b: float = 0.10,
    experiment_id: str = "demo-exp",
) -> pd.DataFrame:
    """
    Generate a deterministic replay/simulation dataset.

    Outcomes are generated from known scenario probabilities. This is for
    demonstrating the decision engine, not for claiming causal impact.
    """
    rng = np.random.default_rng(scenario.seed)
    lead_ids = [f"L{i:07d}" for i in range(n)]

    variants = [
        assign_variant(lead_id, experiment_id, split_b=split_b)
        for lead_id in lead_ids
    ]

    meeting_probs = np.array(
        [scenario.b_rate if v == "B" else scenario.a_rate for v in variants]
    )
    duration_means = np.array(
        [scenario.b_duration if v == "B" else scenario.a_duration for v in variants]
    )

    meeting_fixed = rng.binomial(1, meeting_probs)
    duration = np.maximum(
        10,
        rng.normal(duration_means, 14, size=n),
    ).round(1)

    return pd.DataFrame(
        {
            "lead_id": lead_ids,
            "variant": variants,
            "meeting_fixed": meeting_fixed,
            "call_duration_sec": duration,
            "timestamp": pd.date_range(
                "2026-10-08 09:00:00",
                periods=n,
                freq="s",
            ),
        }
    )


def replay_in_batches(df: pd.DataFrame, batch_size: int = 1000):
    for start in range(0, len(df), batch_size):
        yield df.iloc[start : start + batch_size].copy()
