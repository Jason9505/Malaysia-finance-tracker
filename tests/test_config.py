import pytest


class TestTheme:
    def test_apply_theme_light(self):
        import config as _cfg
        _cfg.apply_theme("light")
        assert _cfg.C_BG == "#f1f5f9"
        assert _cfg.C_CARD == "#ffffff"
        assert _cfg.C_TEXT == "#1e293b"

    def test_apply_theme_dark(self):
        import config as _cfg
        _cfg.apply_theme("dark")
        assert _cfg.C_BG == "#0f172a"
        assert _cfg.C_CARD == "#1e293b"
        assert _cfg.C_TEXT == "#f1f5f9"

    def test_apply_theme_system(self):
        import config as _cfg
        _cfg.apply_theme("system")
        assert _cfg.C_BG is not None
        assert isinstance(_cfg.C_BG, str)

    def test_refresh_theme_propagates(self):
        import config as _cfg
        palette = _cfg.refresh_theme("light")
        assert isinstance(palette, dict)
        assert palette.get("C_BG") == "#f1f5f9"

    def test_theme_resets_correctly(self):
        import config as _cfg
        _cfg.apply_theme("dark")
        assert _cfg.C_BG == "#0f172a"
        _cfg.apply_theme("light")
        assert _cfg.C_BG == "#f1f5f9"


class TestConfigConstants:
    def test_font_ui_is_tuple(self):
        import config as _cfg
        assert isinstance(_cfg.FONT_UI, tuple)
        assert len(_cfg.FONT_UI) >= 2

    def test_tax_bands_are_valid(self):
        import config as _cfg
        total = sum(b[0] for b in _cfg.TAX_BANDS if b[0] != float("inf"))
        last = [b for b in _cfg.TAX_BANDS if b[0] == float("inf")]
        assert len(last) == 1
        assert total > 0

    def test_expense_cats_have_correct_structure(self):
        import config as _cfg
        for key, val in _cfg.EXPENSE_CATS.items():
            assert len(val) == 3
            assert isinstance(val[0], str)
            assert isinstance(val[1], bool)
            assert isinstance(val[2], str)

    def test_all_reliefs_have_correct_structure(self):
        import config as _cfg
        for item in _cfg.ALL_RELIEFS:
            assert len(item) == 3
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)
            assert isinstance(item[2], (int, float))

    def test_nav_items_have_correct_structure(self):
        import config as _cfg
        for item in _cfg.NAV_ITEMS:
            assert len(item) == 3
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)
            assert isinstance(item[2], str)
