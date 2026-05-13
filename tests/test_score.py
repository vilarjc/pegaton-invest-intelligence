"""
Test unitarios para ScoreCombiner (score.py)
Spec ref: docs/architecture.md Sección 3.4, 9.3
"""
import pytest
import pytest
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestDetermineAction:
    """Tests para _determine_action()"""

    def test_action_comprar(self):
        """SPEC: test_action_comprar"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(85.0)
        assert action == "COMPRAR"
        assert emoji == "🔵"

    def test_action_comprar_boundary(self):
        """SPEC: test_action_boundary_80"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(80.0)
        assert action == "COMPRAR"

    def test_action_acumular(self):
        """SPEC: test_action_acumular"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(70.0)
        assert action == "ACUMULAR"
        assert emoji == "🔵"

    def test_action_mantener(self):
        """SPEC: test_action_mantener"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(50.0)
        assert action == "MANTENER"
        assert emoji == "🟡"

    def test_action_reducir(self):
        """SPEC: test_action_reducir"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(30.0)
        assert action == "REDUCIR"
        assert emoji == "🟠"

    def test_action_reducir_boundary(self):
        """SPEC: test_action_boundary_20"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(20.0)
        assert action == "REDUCIR"

    def test_action_evitar(self):
        """SPEC: test_action_evitar"""
        from backend.app.core.score import _determine_action
        action, emoji = _determine_action(10.0)
        assert action == "EVITAR"
        assert emoji == "🔴"

    def test_action_all_boundaries(self):
        """SPEC: test_action_determination_all_ranges"""
        from backend.app.core.score import _determine_action

        assert _determine_action(100)[0] == "COMPRAR"
        assert _determine_action(80)[0] == "COMPRAR"
        assert _determine_action(79)[0] == "ACUMULAR"
        assert _determine_action(60)[0] == "ACUMULAR"
        assert _determine_action(59)[0] == "MANTENER"
        assert _determine_action(40)[0] == "MANTENER"
        assert _determine_action(39)[0] == "REDUCIR"
        assert _determine_action(20)[0] == "REDUCIR"
        assert _determine_action(19)[0] == "EVITAR"
        assert _determine_action(0)[0] == "EVITAR"


class TestPegatonScore:
    """Tests para pegaton_score()"""

    def test_pegaton_score_combines_macro_tech(self, mocker):
        """SPEC: test_pegaton_score_combines_macro_tech"""
        from backend.app.core.score import pegaton_score

        # Mockear macro_score
        mock_macro = {
            "macro_score": 60.0,
            "factors": [
                {"name": "FEDFUNDS", "score": 80.0, "weight": 0.20, "contribution": 16.0, "direction": "alcista"}
            ],
            "details": {}
        }

        # Mockear technical_score
        mock_tech = {
            "technical_score": 70.0,
            "factors": [
                {"name": "RSI(14)", "score": 70.0, "weight": 0.30, "contribution": 21.0, "direction": "alcista"}
            ],
            "details": {}
        }

        mocker.patch("backend.app.core.score.macro_score", return_value=mock_macro)
        mocker.patch("backend.app.core.score.technical_score", return_value=mock_tech)

        result = pegaton_score("SPY")

        # Fórmula: 0.40 * 60 + 0.60 * 70 = 24 + 42 = 66.0
        assert result["pegaton_score"] == 66.0
        assert result["macro_score"] == 60.0
        assert result["technical_score"] == 70.0

    def test_pegaton_score_blend_weights_40_60(self, mocker):
        """SPEC: test_blend_weights_40_60 — verifica peso 40/60"""
        from backend.app.core.score import pegaton_score

        mock_macro = {"macro_score": 50.0, "factors": [], "details": {}}
        mock_tech = {"technical_score": 50.0, "factors": [], "details": {}}

        mocker.patch("backend.app.core.score.macro_score", return_value=mock_macro)
        mocker.patch("backend.app.core.score.technical_score", return_value=mock_tech)

        result = pegaton_score("SPY")

        # 0.40*50 + 0.60*50 = 50.0
        assert result["pegaton_score"] == 50.0

    def test_pegaton_score_dominant_factor(self, mocker):
        """SPEC: test_factor_dominante_correct"""
        from backend.app.core.score import pegaton_score

        mock_macro = {
            "macro_score": 50.0,
            "factors": [
                {"name": "FEDFUNDS", "score": 50.0, "weight": 0.20, "contribution": 10.0, "direction": "neutral"},
                {"name": "UNRATE", "score": 80.0, "weight": 0.15, "contribution": 12.0, "direction": "alcista"},
            ],
            "details": {}
        }

        mock_tech = {
            "technical_score": 60.0,
            "factors": [
                {"name": "RSI(14)", "score": 70.0, "weight": 0.30, "contribution": 21.0, "direction": "alcista"},
                {"name": "MACD", "score": 65.0, "weight": 0.25, "contribution": 16.25, "direction": "alcista"},
                {"name": "SMA50", "score": 50.0, "weight": 0.25, "contribution": 12.5, "direction": "neutral"},
                {"name": "SMA200", "score": 40.0, "weight": 0.20, "contribution": 8.0, "direction": "bajista"},
            ],
            "details": {}
        }

        mocker.patch("backend.app.core.score.macro_score", return_value=mock_macro)
        mocker.patch("backend.app.core.score.technical_score", return_value=mock_tech)

        result = pegaton_score("SPY")

        dominante = result["factors"]["summary"]["factor_dominante"]
        assert dominante["name"] == "RSI(14)"
        assert dominante["contribution"] == 21.0
        assert dominante["direction"] == "alcista"


class TestAllScores:
    """Tests para all_scores()"""

    def test_all_scores_returns_dict(self):
        """SPEC: test_all_scores_returns_all_symbols"""
        from backend.app.core.score import all_scores

        result = all_scores()
        assert isinstance(result, dict)
        # Debe contener al menos SPY
        assert "SPY" in result


class TestScoreSchema:
    """Tests de schema de salida"""

    def test_pegaton_score_output_schema(self, mocker):
        """SPEC: test_pegaton_score_schema"""
        from backend.app.core.score import pegaton_score

        mock_macro = {
            "macro_score": 55.0,
            "factors": [{"name": "X", "score": 55.0, "weight": 0.20, "contribution": 11.0, "direction": "neutral"}],
            "details": {"indicators": {}}
        }
        mock_tech = {
            "technical_score": 65.0,
            "factors": [{"name": "Y", "score": 65.0, "weight": 0.30, "contribution": 19.5, "direction": "alcista"}],
            "details": {}
        }

        mocker.patch("backend.app.core.score.macro_score", return_value=mock_macro)
        mocker.patch("backend.app.core.score.technical_score", return_value=mock_tech)

        result = pegaton_score("SPY")

        # Verificar todas las claves esperadas
        required_keys = ["symbol", "pegaton_score", "action", "macro_score", "technical_score", "factors", "macro_details", "technical_details"]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

        assert result["symbol"] == "SPY"
        assert isinstance(result["pegaton_score"], float)
        assert isinstance(result["action"], str)
        assert "macro" in result["factors"]
        assert "technical" in result["factors"]