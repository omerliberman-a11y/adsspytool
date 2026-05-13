from datetime import UTC, datetime, timedelta

import pytest

from adspy.analyzers.scoring import ScoreInputs, score_ad_row, winner_score


def _inputs(**kwargs: object) -> ScoreInputs:
    defaults: dict[str, object] = {
        "days_active": None,
        "variant_count": None,
        "reach_band": None,
        "placements": None,
        "first_seen": None,
    }
    defaults.update(kwargs)
    return ScoreInputs(**defaults)  # type: ignore[arg-type]


class TestLongevity:
    def test_none_is_zero(self) -> None:
        assert winner_score(_inputs()) == 0

    def test_under_a_week_is_low(self) -> None:
        assert winner_score(_inputs(days_active=3)) <= 5

    def test_thirty_days_is_at_least_25(self) -> None:
        assert winner_score(_inputs(days_active=30)) >= 25

    def test_ninety_days_pegs_longevity(self) -> None:
        s90 = winner_score(_inputs(days_active=90))
        s365 = winner_score(_inputs(days_active=365))
        assert s90 == s365  # longevity component saturates at 90

    def test_negative_days_safe(self) -> None:
        assert winner_score(_inputs(days_active=-5)) == 0


class TestVariants:
    def test_one_variant_is_almost_nothing(self) -> None:
        assert winner_score(_inputs(variant_count=1)) <= 5

    def test_five_variants_meaningful(self) -> None:
        assert winner_score(_inputs(variant_count=5)) >= 15

    def test_twenty_variants_pegs(self) -> None:
        assert winner_score(_inputs(variant_count=20)) == winner_score(_inputs(variant_count=100))

    def test_zero_or_none_treated_same(self) -> None:
        assert winner_score(_inputs(variant_count=0)) == winner_score(_inputs(variant_count=None))


class TestReach:
    def test_high_reach_band(self) -> None:
        assert winner_score(_inputs(reach_band=">1000000")) >= 18

    def test_low_reach_band(self) -> None:
        assert winner_score(_inputs(reach_band="<1000")) <= 2

    def test_unknown_band_is_zero(self) -> None:
        assert winner_score(_inputs(reach_band="banana")) == 0


class TestPlacements:
    def test_one_placement(self) -> None:
        assert winner_score(_inputs(placements=("facebook",))) <= 3

    def test_four_placements_pegs(self) -> None:
        s4 = winner_score(_inputs(placements=("facebook", "instagram", "messenger", "threads")))
        s10 = winner_score(
            _inputs(placements=("facebook", "instagram", "messenger", "threads", "an", "x"))
        )
        assert s4 == s10
        assert s4 >= 9

    def test_dedupes(self) -> None:
        assert winner_score(_inputs(placements=("facebook", "facebook"))) == winner_score(
            _inputs(placements=("facebook",))
        )


class TestRecencyBonus:
    def test_old_ad_no_bonus(self) -> None:
        old = datetime.now(UTC) - timedelta(days=60)
        with_first = winner_score(_inputs(variant_count=10, first_seen=old))
        without_first = winner_score(_inputs(variant_count=10))
        assert with_first == without_first

    def test_new_ad_with_signals_gets_bonus(self) -> None:
        new = datetime.now(UTC) - timedelta(days=5)
        bonus = winner_score(_inputs(variant_count=10, first_seen=new))
        no_bonus = winner_score(_inputs(variant_count=10))
        assert bonus > no_bonus

    def test_new_ad_no_signals_no_bonus(self) -> None:
        new = datetime.now(UTC) - timedelta(days=5)
        assert winner_score(_inputs(first_seen=new)) == 0


class TestCombined:
    def test_full_winner(self) -> None:
        s = winner_score(
            _inputs(
                days_active=120,
                variant_count=15,
                reach_band=">1000000",
                placements=("facebook", "instagram", "messenger", "threads"),
            )
        )
        assert s >= 90

    def test_zero_signal(self) -> None:
        assert winner_score(_inputs()) == 0

    @pytest.mark.parametrize("score", [winner_score(_inputs(days_active=d)) for d in (0, 30, 90)])
    def test_scores_bounded_0_100(self, score: int) -> None:
        assert 0 <= score <= 100


class TestScoreAdRow:
    def test_dict_passthrough(self) -> None:
        ad = {
            "days_active": 120,
            "variant_count": 15,
            "reach_band": ">1000000",
            "placements": ["facebook", "instagram", "messenger", "threads"],
            "first_seen": None,
        }
        assert score_ad_row(ad) >= 90

    def test_missing_keys_safe(self) -> None:
        assert score_ad_row({}) == 0
