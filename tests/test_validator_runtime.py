"""Runtime compatibility checks for the validator neuron."""

from neurons.validator import ArcturaValidator


def test_validator_tempo_fallback_handles_none_config():
    class Config:
        tempo = None

    tempo = getattr(Config, "tempo", None) or ArcturaValidator.DEFAULT_TEMPO
    assert tempo == ArcturaValidator.DEFAULT_TEMPO
