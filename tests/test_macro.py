"""
Test unitarios para MacroEngine
Spec ref: docs/architecture.md Sección 3.1, 9.1
"""
import pytest
import sqlite3
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture
def temp_db():
    """Crea una base de datos SQLite temporal para tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE macro_indicators (date TEXT, indicator TEXT, value REAL)")
    yield conn, path
    conn.close()
    os.close(fd)
    os.unlink(path)


class TestMacroScore:
    """Tests para macro_score() — Spec ref: Sección 3.1"""

    def test_macro_score_empty_db(self, temp_db):
        """SPEC: test_macro_score_returns_valid_schema con DB vacía"""
        conn, path = temp_db
        # Sobrescribir DB_PATH temporalmente
        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()
        assert result["macro_score"] == 50
        assert "error" in result.get("details", {})
        assert result["factors"] == []

        macro_mod.DB_PATH = original

    def test_macro_score_with_fred_data(self, temp_db):
        """SPEC: test_macro_score_with_test_data — valores conocidos"""
        conn, path = temp_db

        # Insertar datos de prueba para todos los 8 indicadores
        test_data = [
            ("2026-05-01", "FEDFUNDS", 1.5),    # Score esperado: 80
            ("2026-05-01", "CPIAUCSL", 300.0),  # Score esperado: 50 (default)
            ("2026-05-01", "PCEPI", 295.0),      # Score esperado: 50 (default)
            ("2026-05-01", "PAYEMS", 170000),    # Score esperado: 70
            ("2026-05-01", "UNRATE", 3.8),       # Score esperado: 70
            ("2026-05-01", "UMCSENT", 105.0),    # Score esperado: 80
            ("2026-05-01", "INDPRO", 110.0),     # Score esperado: 70
            ("2026-05-01", "DGS10", 3.5),        # Score esperado: 55
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()

        assert "macro_score" in result
        assert 0 <= result["macro_score"] <= 100
        assert len(result["factors"]) == 8

        # Verificar contribuciones individuales
        contributions = {f["name"]: f["contribution"] for f in result["factors"]}
        # FEDFUNDS: 80 * 0.20 = 16.0
        assert contributions["FEDFUNDS"] == 16.0
        # PAYEMS: 70 * 0.15 = 10.5
        assert contributions["PAYEMS"] == 10.5

        macro_mod.DB_PATH = original

    def test_macro_factor_directions(self, temp_db):
        """SPEC: test_macro_direction_classification"""
        conn, path = temp_db

        test_data = [
            ("2026-05-01", "FEDFUNDS", 1.0),    # Muy bajo → score alto → alcista
            ("2026-05-01", "UNRATE", 7.0),      # Muy alto → score bajo → bajista
            ("2026-05-01", "CPIAUCSL", 300.0),  # Default → neutral
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()

        directions = {f["name"]: f["direction"] for f in result["factors"]}
        assert directions["FEDFUNDS"] == "alcista"
        assert directions["UNRATE"] == "bajista"

        macro_mod.DB_PATH = original

    def test_macro_all_indicators_processed(self, temp_db):
        """SPEC: test_macro_all_indicators_processed"""
        conn, path = temp_db

        test_data = [
            ("2026-05-01", "FEDFUNDS", 2.0),
            ("2026-05-01", "CPIAUCSL", 300.0),
            ("2026-05-01", "PCEPI", 295.0),
            ("2026-05-01", "PAYEMS", 150000),
            ("2026-05-01", "UNRATE", 4.0),
            ("2026-05-01", "UMCSENT", 85.0),
            ("2026-05-01", "INDPRO", 100.0),
            ("2026-05-01", "DGS10", 4.5),
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()
        assert len(result["factors"]) == 8

        # Verificar que todos los pesos suman 1.0
        total_weight = sum(f["weight"] for f in result["factors"])
        assert abs(total_weight - 1.0) < 0.001

        macro_mod.DB_PATH = original

    def test_macro_score_returns_valid_schema(self, temp_db):
        """SPEC: test_macro_score_returns_valid_schema"""
        conn, path = temp_db

        test_data = [
            ("2026-05-01", "FEDFUNDS", 2.0),
            ("2026-05-01", "CPIAUCSL", 300.0),
            ("2026-05-01", "PCEPI", 295.0),
            ("2026-05-01", "PAYEMS", 150000),
            ("2026-05-01", "UNRATE", 4.0),
            ("2026-05-01", "UMCSENT", 85.0),
            ("2026-05-01", "INDPRO", 100.0),
            ("2026-05-01", "DGS10", 4.5),
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()

        # Verificar schema
        assert isinstance(result, dict)
        assert "macro_score" in result
        assert "factors" in result
        assert "details" in result
        assert isinstance(result["macro_score"], (int, float))
        assert 0 <= result["macro_score"] <= 100

        for factor in result["factors"]:
            assert "name" in factor
            assert "score" in factor
            assert "weight" in factor
            assert "contribution" in factor
            assert "direction" in factor
            assert factor["direction"] in ("alcista", "bajista", "neutral")
            assert 0 <= factor["score"] <= 100

        macro_mod.DB_PATH = original


class TestMacroWeights:
    """Tests para verificar pesos correctos"""

    def test_macro_weights_sum_one(self):
        """SPEC: test_macro_factors_sum_weights_1"""
        from backend.app.core.pegaton_config import MACRO_WEIGHTS
        total = sum(MACRO_WEIGHTS.values())
        assert abs(total - 1.0) < 0.0001


class TestMacroScoreBoundaries:
    """Tests de límites del score"""

    def test_macro_score_floor_zero(self, temp_db):
        """SPEC: test_macro_score_boundary_0 — todos los indicadores en mínimos"""
        conn, path = temp_db

        # Valores extremadamente malos
        test_data = [
            ("2026-05-01", "FEDFUNDS", 10.0),    # Score: 20
            ("2026-05-01", "CPIAUCSL", 500.0),   # Score: 50 (default)
            ("2026-05-01", "PCEPI", 500.0),       # Score: 50 (default)
            ("2026-05-01", "PAYEMS", 50000),      # Score: 30
            ("2026-05-01", "UNRATE", 15.0),       # Score: 20
            ("2026-05-01", "UMCSENT", 20.0),       # Score: 20
            ("2026-05-01", "INDPRO", 80.0),        # Score: 40
            ("2026-05-01", "DGS10", 10.0),         # Score: 25
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()
        assert 0 <= result["macro_score"] <= 100

        macro_mod.DB_PATH = original

    def test_macro_score_ceiling_100(self, temp_db):
        """SPEC: test_macro_score_boundary_100 — todos los indicadores en máximos"""
        conn, path = temp_db

        # Valores excelentes
        test_data = [
            ("2026-05-01", "FEDFUNDS", 1.0),      # Score: 80
            ("2026-05-01", "CPIAUCSL", 100.0),    # Score: 50 (default)
            ("2026-05-01", "PCEPI", 100.0),        # Score: 50 (default)
            ("2026-05-01", "PAYEMS", 300000),      # Score: 70
            ("2026-05-01", "UNRATE", 2.0),         # Score: 80
            ("2026-05-01", "UMCSENT", 120.0),       # Score: 80
            ("2026-05-01", "INDPRO", 150.0),        # Score: 70
            ("2026-05-01", "DGS10", 4.5),           # Score: 55
        ]
        conn.executemany(
            "INSERT INTO macro_indicators (date, indicator, value) VALUES (?, ?, ?)",
            test_data,
        )
        conn.commit()

        import backend.app.core.macro as macro_mod
        original = macro_mod.DB_PATH
        macro_mod.DB_PATH = path

        result = macro_mod.macro_score()
        assert 0 <= result["macro_score"] <= 100

        macro_mod.DB_PATH = original