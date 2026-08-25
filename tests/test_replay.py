from huntlab.actions.replay import ReplaySink
from huntlab.config import ScenarioConfig
from huntlab.engine import AgentEngine
from huntlab.perception.fixture import FixturePerceptor
from huntlab.sources import JsonlSource


def test_fixture_reaches_shiny_terminal_state() -> None:
    config = ScenarioConfig.load("scenarios/magikarp_fishing.yaml")
    sink = ReplaySink()
    engine = AgentEngine(
        session_id="test-replay",
        config=config,
        perceptor=FixturePerceptor(),
        sink=sink,
    )
    result = engine.run(JsonlSource("fixtures/magikarp_normal_then_shiny.jsonl"))
    assert result.state.halted
    assert result.state.halt_reason == "shiny_threshold_reached"
    assert result.state.encounters == 2
    assert result.state.target_encounters == 2
    assert sink.proposals[-1].kind.value == "alert_shiny"
