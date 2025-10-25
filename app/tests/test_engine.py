from datetime import datetime

from ..core.engine import ETAEngine
from ..core.traffic import TrafficModel


class DummyTrafficModel(TrafficModel):
    def __init__(self) -> None:
        super().__init__()

    def multiplier(self, lat: float, lon: float, moment=None, profile: str = "default") -> float:
        return 1.0


def test_eta_engine_single():
    traffic = DummyTrafficModel()
    engine = ETAEngine(traffic, use_cpp=False)

    eta = engine.eta_seconds((52.37, 4.89), (52.52, 13.4), 90)

    assert eta > 0
    assert engine.cache_info()["misses"] == 1
    # second call should hit cache
    eta_cached = engine.eta_seconds((52.37, 4.89), (52.52, 13.4), 90)
    assert eta_cached == eta
    assert engine.cache_info()["hits"] == 1


def test_route_eta_accumulates_departure():
    traffic = DummyTrafficModel()
    engine = ETAEngine(traffic, use_cpp=False)

    start = datetime.utcnow()
    total, legs = engine.route_eta(
        [(52.37, 4.89), (52.4, 4.95), (52.5, 5.0)],
        40,
        departure=start,
    )

    assert len(legs) == 2
    assert total == sum(legs)


def test_matrix_eta_accounts_for_profiles():
    traffic = TrafficModel()
    traffic.set_hourly_multiplier(8, 0.5)
    engine = ETAEngine(traffic, use_cpp=False)

    matrix = engine.matrix_eta([(52.37, 4.89)], [(52.52, 13.4)], 60)
    assert len(matrix) == 1
    assert len(matrix[0]) == 1
    assert matrix[0][0] > 0
