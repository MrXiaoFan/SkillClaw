# -*- coding: utf-8 -*-
"""Unit test for D1 reject_ready settle guard in _finalize_validation_jobs.

The guard is: once len(results) >= validation_required_results and the job is
NOT publishable, the job must be rejected (settle) instead of remaining pending
forever (the old reject_ready only tripped at max_rejections).
"""
import pytest

def _settle_decision(*, results, required_results, required_approvals,
                     max_rejections, min_score, threshold, gate_passed):
    """Replicate the post-D1 decision logic from _finalize_validation_jobs.

    Returns ("pending"|"published"|"rejected").
    """
    accepted = sum(1 for r in results if r.get("accepted") is True)
    rejected = sum(1 for r in results if r.get("accepted") is not True)
    mean = (sum(float(r["score"]) for r in results) / len(results)) if results else None

    if gate_passed is None:
        gate_passed = mean is not None and mean >= threshold

    publish_ready = (
        len(results) >= required_results
        and accepted >= required_approvals
        and gate_passed
    )
    reject_ready = rejected >= max_rejections
    # D1 guard
    if not publish_ready and len(results) >= required_results:
        reject_ready = True

    if publish_ready:
        return "published"
    if reject_ready:
        return "rejected"
    return "pending"


def mk(accepted=True, score=0.7):
    return {"accepted": accepted, "score": score}


def test_single_rejected_result_settles_as_rejected_not_stuck():
    # required_results=1, required_approvals=1, max_rejections=3
    # One rejected result that never reaches max_rejections used to hang forever.
    out = _settle_decision(
        results=[mk(accepted=False, score=0.5)],
        required_results=1, required_approvals=1,
        max_rejections=3, min_score=0.75, threshold=0.6, gate_passed=False,
    )
    assert out == "rejected"


def test_publishable_job_still_publishes():
    out = _settle_decision(
        results=[mk(accepted=True, score=0.8)],
        required_results=1, required_approvals=1,
        max_rejections=3, min_score=0.75, threshold=0.6, gate_passed=True,
    )
    assert out == "published"


def test_below_required_results_stays_pending():
    # Only 0 results -> must stay pending because not enough evidence yet.
    out = _settle_decision(
        results=[],
        required_results=1, required_approvals=1,
        max_rejections=3, min_score=0.75, threshold=0.6, gate_passed=False,
    )
    assert out == "pending"


def test_rejected_with_result_count_below_required_stays_pending():
    # required_results=2, only 1 result (rejected) -> not settled yet.
    out = _settle_decision(
        results=[mk(accepted=False, score=0.3)],
        required_results=2, required_approvals=1,
        max_rejections=3, min_score=0.75, threshold=0.6, gate_passed=False,
    )
    assert out == "pending"


def test_mixed_accepted_rejected_publish_when_gate_passes():
    out = _settle_decision(
        results=[mk(accepted=True, score=0.8), mk(accepted=False, score=0.4)],
        required_results=2, required_approvals=1,
        max_rejections=3, min_score=0.75, threshold=0.6, gate_passed=True,
    )
    assert out == "published"
