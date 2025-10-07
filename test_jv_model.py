# test_jm_model.py
import pytest
from jelinski_moranda import compute

variants = {
    1: [9,12,11,4,7,2,5,8,5,7,1,6,1,9,4,1,3,3,6,1,1,11,33,7,91,2],
    2: [7,10,12,6,7,3,5,9,5,7,2,6,1,8,3,1,2,3,5,1,84,30,7,3,1],
    3: [5,4,11,13,6,2,7,5,8,7,1,4,2,7,6,2,3,1,4,78,25,10,7,16,3,1,2],
    4: [5,8,12,7,6,4,3,7,8,5,2,9,3,6,5,2,4,3,77,2,9,8,10,1,5,3,4,2],
    5: [4,13,10,5,8,1,6,7,4,9,5,2,3,8,6,3,2,3,94,5,12,8,28,3],
}

def print_header():
    print("\n### Jelinski–Moranda model results\n")
    print("| Variant | n |  B̂ (total errors) |  K̂ (rate) |  Xₙ₊₁ (next err, h) |  T_finish (h) | Iter | Converged |")
    print("|:--------:|--:|------------------:|-----------:|--------------------:|---------------:|------:|-----------:|")

@pytest.mark.parametrize("v,X", variants.items())
def test_all_variants(v, X):
    res = compute(X)
    assert res["converged"], f"❌ Variant {v}: метод Ньютона не сошёлся"
    assert res["B_hat"] > len(X), f"❌ Variant {v}: B_hat ≤ n"
    assert res["K_hat"] > 0, f"❌ Variant {v}: K_hat отрицательный"

    # печать аккуратной строки таблицы
    print(f"| {v} | {res['n']} | {res['B_hat']:.4f} | {res['K_hat']:.6e} | "
          f"{res['X_next']:.4f} | {res['time_to_finish']:.4f} | "
          f"{res['iterations']} | {res['converged']} |")

@pytest.fixture(scope="session", autouse=True)
def banner():
    """Вывод заголовка таблицы перед тестами"""
    print_header()
