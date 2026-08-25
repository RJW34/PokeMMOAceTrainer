from huntlab.actions.replay import ReplaySink
from huntlab.config import ScenarioConfig
from huntlab.engine import AgentEngine
from huntlab.perception.fixture import FixturePerceptor
from huntlab.simulator.fishing import FishingSimulator


def run(seed: int) -> tuple[int, int, bool, str | None, list[str]]:
    config = ScenarioConfig.load("scenarios/magikarp_fishing.yaml")
    sink = ReplaySink()
    engine = AgentEngine(
        session_id=f"sim-{seed}",
        config=config,
        perceptor=FixturePerceptor(),
        sink=sink,
    )
    result = engine.run(FishingSimulator(config, seed=seed), max_steps=1000)
    return (
        result.steps,
        result.state.encounters,
        result.state.halted,
        result.state.halt_reason,
        [p.kind.value for p in sink.proposals],
    )


def test_fixed_seed_is_deterministic() -> None:
    assert run(7) == run(7)


def test_simulator_produces_a_trace() -> None:
    steps, encounters, _, _, proposals = run(7)
    assert steps > 0
    assert encounters >= 0
    assert proposals
