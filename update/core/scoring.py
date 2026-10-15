"""Talent score. Benchmarks are ILLUSTRATIVE - replace with official norms."""
import numpy as np

AGE_MIN, AGE_MAX = 10, 25

def age_ok(age):
    return AGE_MIN <= age <= AGE_MAX

def age_band(age):
    return "U14" if age < 14 else "14-17" if age < 18 else "18+"

def _norms(m1, m2, m3, f1, f2, f3):
    return {("Male", "U14"): m1, ("Male", "14-17"): m2, ("Male", "18+"): m3,
            ("Female", "U14"): f1, ("Female", "14-17"): f2, ("Female", "18+"): f3}

# (value worth 0 points, value worth 100 points)
JUMP_NORMS = _norms((15, 50), (20, 60), (25, 70), (12, 40), (15, 48), (18, 55))      # cm
SPRINT_NORMS = _norms((6.5, 4.9), (6.0, 4.5), (5.6, 4.2), (7.0, 5.3), (6.6, 5.0), (6.2, 4.8))  # 30 m, s
BROAD_NORMS = _norms((100, 200), (140, 250), (170, 270), (90, 170), (110, 205), (130, 220))    # cm
SHUTTLE_NORMS = _norms((14, 11), (13, 10), (12.5, 9.5), (15, 12), (14, 11), (13.5, 10.5))      # 4x10 m, s
RUN_NORMS = _norms((12, 7.5), (11, 6.5), (10.5, 6), (13.5, 9), (12.5, 8), (12, 7.5))           # 1.6 km, min

def _scale(v, lo, hi):
    return float(np.clip((v - lo) / (hi - lo) * 100, 0, 100))

def talent_score(gender, age, jump_cm=None, sprint_s=None, broad_cm=None, shuttle_s=None, run_min=None):
    b = (gender, age_band(age))
    parts = [_scale(v, *n[b]) for v, n in ((jump_cm, JUMP_NORMS), (sprint_s, SPRINT_NORMS),
             (broad_cm, BROAD_NORMS), (shuttle_s, SHUTTLE_NORMS), (run_min, RUN_NORMS)) if v is not None]
    return round(float(np.mean(parts)), 1) if parts else 0.0

def percentile(score, peer_scores):
    if len(peer_scores) == 0:
        return 100.0
    return round(100 * float(np.mean(np.array(peer_scores) <= score)), 1)
