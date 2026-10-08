from dataclasses import dataclass
from math import sqrt
from scipy.stats import norm


@dataclass
class Decision:
    status: str
    p_value: float
    lift: float
    diff: float
    ci_low: float
    ci_high: float
    a_rate: float
    b_rate: float
    reason: str


def _safe_rate(successes: int, n: int) -> float:
    return successes / n if n else 0.0


def compare_binary_rates(
    a_success: int,
    a_n: int,
    b_success: int,
    b_n: int,
    alpha: float = 0.01,
) -> tuple[float, float, float, float]:
    """
    Two-sided two-proportion z-test.

    Returns:
        p_value, diff(B-A), ci_low, ci_high
    """
    if a_n <= 0 or b_n <= 0:
        return 1.0, 0.0, float("-inf"), float("inf")

    pa = a_success / a_n
    pb = b_success / b_n
    diff = pb - pa

    pooled = (a_success + b_success) / (a_n + b_n)
    se_pooled = sqrt(max(pooled * (1 - pooled) * (1 / a_n + 1 / b_n), 1e-15))
    z = diff / se_pooled
    p_value = 2 * norm.sf(abs(z))

    zcrit = norm.ppf(1 - alpha / 2)
    se_unpooled = sqrt(
        max(
            pa * (1 - pa) / a_n + pb * (1 - pb) / b_n,
            1e-15,
        )
    )
    ci_low = diff - zcrit * se_unpooled
    ci_high = diff + zcrit * se_unpooled

    return p_value, diff, ci_low, ci_high


def relative_lift(a_rate: float, b_rate: float) -> float:
    if a_rate <= 0:
        return 0.0
    return (b_rate - a_rate) / a_rate


def decide(
    a_success: int,
    a_n: int,
    b_success: int,
    b_n: int,
    alpha: float = 0.01,
    min_per_arm: int = 1000,
) -> Decision:
    a_rate = _safe_rate(a_success, a_n)
    b_rate = _safe_rate(b_success, b_n)

    if a_n < min_per_arm or b_n < min_per_arm:
        return Decision(
            status="INCONCLUSIVE",
            p_value=1.0,
            lift=relative_lift(a_rate, b_rate),
            diff=b_rate - a_rate,
            ci_low=float("-inf"),
            ci_high=float("inf"),
            a_rate=a_rate,
            b_rate=b_rate,
            reason=f"Minimum sample not reached ({min_per_arm:,} per arm required).",
        )

    p, diff, lo, hi = compare_binary_rates(
        a_success, a_n, b_success, b_n, alpha=alpha
    )

    lift = relative_lift(a_rate, b_rate)

    if p < alpha and lo > 0 and b_rate > a_rate:
        status = "WIN"
        reason = "Treatment is statistically better and its confidence interval is entirely above zero."
    elif p < alpha and hi < 0 and b_rate < a_rate:
        status = "STOP"
        reason = "Treatment is statistically worse and its confidence interval is entirely below zero."
    else:
        status = "INCONCLUSIVE"
        reason = "Evidence is insufficient to safely promote or stop treatment."

    return Decision(
        status=status,
        p_value=p,
        lift=lift,
        diff=diff,
        ci_low=lo,
        ci_high=hi,
        a_rate=a_rate,
        b_rate=b_rate,
        reason=reason,
    )
