from rea_score.lily_convert import render_length
from rea_score.primitives import Length


def test_render_length() -> None:
    assert render_length(Length(5 / 8 * 4)) == ('2', '~ 8')