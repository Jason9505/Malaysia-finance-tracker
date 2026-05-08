import pytest
from utils import fmt_rm, calc_malaysia_tax, get_tax_rebate, compute_full_tax, build_bracket_rows


class TestFormatting:
    def test_fmt_rm_basic(self):
        assert fmt_rm(1000) == "RM 1,000.00"

    def test_fmt_rm_zero(self):
        assert fmt_rm(0) == "RM 0.00"

    def test_fmt_rm_large(self):
        assert fmt_rm(1_234_567.89) == "RM 1,234,567.89"

    def test_fmt_rm_negative(self):
        assert fmt_rm(-500) == "RM -500.00"


class TestTaxCalculation:
    def test_zero_chargeable(self):
        assert calc_malaysia_tax(0) == 0.0

    def test_below_first_band(self):
        assert calc_malaysia_tax(5000) == 0.0

    def test_first_band(self):
        tax = calc_malaysia_tax(10000)
        assert tax == pytest.approx(5000 * 0 + 5000 * 0.01)

    def test_third_band(self):
        tax = calc_malaysia_tax(30000)
        expected = (5000 * 0.00 + 15000 * 0.01 + 10000 * 0.03)
        assert tax == pytest.approx(expected)

    def test_full_progression(self):
        tax = calc_malaysia_tax(100000)
        expected = (5000 * 0.00 + 15000 * 0.01 + 15000 * 0.03 +
                    15000 * 0.08 + 20000 * 0.13 + 30000 * 0.21)
        assert tax == pytest.approx(expected)


class TestTaxRebate:
    def test_rebate_below_threshold(self):
        assert get_tax_rebate(35000) == 400.0

    def test_rebate_at_threshold(self):
        assert get_tax_rebate(35000) == 400.0

    def test_no_rebate_above_threshold(self):
        assert get_tax_rebate(35001) == 0.0

    def test_rebate_zero_income(self):
        assert get_tax_rebate(0) == 400.0


class TestComputeFullTax:
    def test_basic_computation(self):
        result = compute_full_tax(80000, 20000)
        assert result["gross"] == 80000
        assert result["reliefs"] == 20000
        assert result["chargeable"] == 60000
        assert result["net_tax"] >= 0
        assert result["eff_rate"] > 0

    def test_no_income(self):
        result = compute_full_tax(0, 0)
        assert result["chargeable"] == 0
        assert result["net_tax"] == 0
        assert result["eff_rate"] == 0

    def test_reliefs_exceed_income(self):
        result = compute_full_tax(10000, 20000)
        assert result["chargeable"] == 0
        assert result["net_tax"] == 0


class TestBracketRows:
    def test_zero_chargeable(self):
        rows = build_bracket_rows(0)
        assert len(rows) == 0

    def test_single_bracket(self):
        rows = build_bracket_rows(5000)
        assert len(rows) == 1
        assert rows[0][2] == 5000

    def test_multi_bracket(self):
        rows = build_bracket_rows(25000)
        assert len(rows) >= 2
        total_tax = sum(r[3] for r in rows)
        assert total_tax == pytest.approx(calc_malaysia_tax(25000))
