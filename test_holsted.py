import math
from holstead_lab3 import TABLE, run_all_for_variant

def test_run_variant_basic_properties():
    data = TABLE[2]
    # используем небольшую нагрузку: m=3, nu=20, work_day_hours=8 (как в CLI по умолчанию)
    results = run_all_for_variant(data, m=3, nu=20, work_day_hours=8)

    # базовые проверки структуры
    assert isinstance(results, dict)
    assert "n2_star" in results
    assert "V_star" in results
    assert "ratings" in results
    assert isinstance(results["ratings"], dict)
    assert set(results["ratings"].keys()) == {1, 2, 3}

    # n2_star > 0, V_star > 0
    assert results["n2_star"] > 0
    assert results["V_star"] > 0

    # потенциальное число ошибок положительное
    assert results["B1_from_Vstar_lambda"] > 0
    assert results["B2_from_V"] > 0

    # t_k либо бесконечность, либо положительное число
    t_k = results["t_k"]
    assert t_k == float('inf') or (isinstance(t_k, float) and t_k > 0)

    # значения рейтинга и ожидаемых ошибок конечны (не NaN)
    for v in results["ratings"].values():
        assert math.isfinite(v["R_new"])
        assert math.isfinite(v["B_expected_next"])
