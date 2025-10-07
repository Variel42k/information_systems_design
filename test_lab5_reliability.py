import pytest
from lab5 import compute_all

@pytest.mark.parametrize(
"variant,params",
[
(
2,
dict(
Q=6,
N=1200,
Tv_samples=[0.8, 1.4],
T_dopV=0.95,
Tpi_samples=[8, 12],
T_dopp=14,
P_baz=0.94,
),
),
],
)
def test_reliability_variant(capsys, variant, params):
"""Проверка расчета фактора надежности по ГОСТ 28195-89 для указанного варианта."""
result = compute_all(**params)

print(f"\n=== РЕЗУЛЬТАТ РАСЧЕТА ФАКТОРА НАДЕЖНОСТИ — Вариант {variant} ===")
for key, val in result.items():
    if isinstance(val, float):
        print(f"{key:70s}: {val:.4f}")
    else:
        print(f"{key:70s}: {val}")

# Проверки корректности
assert 0 <= result["Фактор качества (надежность ПС) (KiФ)"] <= 1
assert result["Н0401 — вероятность безотказной работы (P)"] <= 1.0
assert result["Н0501 — по среднему времени восстановления (Qв)"] <= 1.0
assert result["Н0502 — по времени преобразования (среднее по всем наборам) (Qпi)"] <= 1.0

captured = capsys.readouterr()
assert "РЕЗУЛЬТАТ РАСЧЕТА" in captured.out