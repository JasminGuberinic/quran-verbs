"""Tests for the resource governor — the limit that says no instead of advising it."""

import pytest

from fil.conjugation import QutrubConjugator
from fil.governor import BudgetExceeded, is_heavy, permit


class _HeavyGenerator:
    is_heavy = True


class _UndeclaredGenerator:
    """A generator that says nothing about its cost."""


def test_a_light_run_is_allowed_at_any_size():
    permit(1473, [QutrubConjugator()])  # must not raise


def test_a_heavy_generator_over_the_whole_catalogue_is_refused():
    with pytest.raises(BudgetExceeded) as refusal:
        permit(1473, [QutrubConjugator(), _HeavyGenerator()])

    assert "batches" in str(refusal.value), "a refusal must say what to do instead"
    assert "_HeavyGenerator" in str(refusal.value)


def test_a_heavy_generator_within_the_cap_is_allowed():
    permit(40, [_HeavyGenerator()], cap=60)  # must not raise


def test_cost_defaults_to_cheap_when_a_generator_does_not_declare_it():
    assert not is_heavy(_UndeclaredGenerator())
    permit(1473, [_UndeclaredGenerator()])  # must not raise
