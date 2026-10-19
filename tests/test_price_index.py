from math import isclose

from src.price_index import factors, to_2023


def test_cpi_rebases_price_years_to_2023():
    f = factors()
    assert set(f) == {2021, 2022, 2023, 2024, 2025}
    assert f[2023] == 1.0
    assert isclose(to_2023(100, 2024), 100 * f[2024])
    assert 0.95 < f[2025] < 1.0
