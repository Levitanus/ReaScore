from fractions import Fraction

from rea_score.primitives import NotationPitch

import rea_score.primitives as pr

from copy import deepcopy

from rea_score.scale import Accidental


class FracturedConcrete(pr.Fractured):

    def __init__(self, numerator: int, denominator: int) -> None:
        self._fraction = Fraction(numerator=numerator, denominator=denominator)
        self.numerator = numerator
        self.denominator = denominator

    @property
    def fraction(self) -> Fraction:
        return self._fraction


def test_simple() -> None:
    fr1 = FracturedConcrete(1, 4)
    fr2 = FracturedConcrete(1, 8)
    assert fr1 > fr2
    assert fr2 * 2 == Fraction(1 / 4)
    assert fr2 * 2 == fr1.fraction
    assert Fraction(1 / 4) / 2 == Fraction(1 / 8)
    print(fr1 / 2)
    assert fr1 / 2 == fr2


def test_notmalized() -> None:
    fr1 = FracturedConcrete(9, 16)
    assert fr1.normalized(fr1.fraction) == (Fraction(1 / 16), Fraction(1 / 2))


def test_position() -> None:
    pos1 = pr.Position(3)
    assert pos1.bar == 1
    assert pos1.bar_position == 3 / 4
    assert pos1.position == 3
    assert pos1.bar_end_distance == 1 / 4
    assert pos1 == pr.Position.from_fraction(3 / 4)

    pos2 = pr.Position(6.5)
    assert pos2.bar == 2
    assert pos2.bar_position == 5 / 8
    assert pos2.position == 6.5
    assert pos1 < pos2
    assert str(pos2) == '<Position bar:2, beat:5/8, from start:6.5>'

    assert pos2.bar_position_norm == (1 / 2, 1 / 8)  # type:ignore
    pos3 = pr.Position(4 + 2 + 1 + 1 / 2 + 1 / 4)
    assert pos3.bar_position_norm == (1 / 2, 1 / 4, 3 / 16)  # type:ignore

    assert pos1.percize_distance(pr.Position(3)) is None
    assert pos1.percize_distance(pos2) == pos2.percize_distance(pos1)
    assert pr.Position(3).percize_distance(pos2) == (
        pr.Length(1), 1, pr.Length(2.5)
    )
    assert pr.Position(3).percize_distance(
        pr.Position(21.5)
    ) == (pr.Length(1), 5, pr.Length(1.5))


def test_length() -> None:
    len1 = pr.Length(17 / 8 * 4)
    assert len1 > 1
    assert len1 > 2
    assert len1 // 1 == 2
    assert len1 % 1 == 1 / 8
    assert len1 == pr.Length.from_fraction(17 / 8)
    assert str(len1) == '<Length 17/8>'


def test_pitch() -> None:
    p1 = pr.Pitch()
    assert p1.named_pitch() == 'r'
    assert str(p1) == '<Pitch is rest>'

    p2 = pr.Pitch(60)
    assert p1 != p2
    assert p2.named_pitch() == 'c4'
    p2.accidental = Accidental.es
    assert p2.named_pitch() == 'c4'
    p2.accidental = Accidental.is_
    assert p2.named_pitch() == 'b♯3'

    p3 = pr.Pitch(61, accidental=Accidental.es)
    p33 = pr.Pitch(61, accidental=Accidental.es)
    assert p3 == p33
    p4 = pr.Pitch(61, accidental=Accidental.is_)
    assert p3 in p4
    assert str(p3) == '<Pitch midi:61, d♭4 (in c:major), tie=False>'


def test_event() -> None:
    assert str(pr.Event(pr.Length(15 / 16 * 4), pr.Pitch(58))) == (
        '<Event (<Length 15/16>, <Pitch midi:58, a♯3' +
        ' (in c:major), tie=False>, 1, [])>'
    )

    ev = pr.Event(pr.Length(2), pr.Pitch(60, tie=True))
    assert ev is not deepcopy(ev)
    copy = deepcopy(ev)
    copy.pitch.tie = False
    assert ev.pitch != copy.pitch
    left = pr.Event(pr.Length(1.5), pr.Pitch(60, tie=True))
    right = pr.Event(pr.Length(0.5), pr.Pitch(60, tie=True))
    split = ev.split(pr.Length(1.5))
    assert split == (left, right)


def test_chord() -> None:
    chord = pr.Chord(
        pr.Length(1 / 2 * 4), pitches=[pr.Pitch(60),
                                       pr.Pitch(64)]
    )
    left, right = chord.split(pr.Length(1 / 8 * 4))
    assert left.length == Fraction(1 / 8)
    assert right.length == Fraction(3 / 8)
    assert left.pitches == right.pitches == chord.pitches
    left, right = chord.split(pr.Length(1 / 8 * 4), tie=True)
    assert left.pitches != right.pitches
    assert left.pitches[0].tie is True


def test_notation_pitch() -> None:
    assert NotationPitch.reascore_tokens(
        'NOTE 0 69 text ReaScore|accidental:isis articulation accent ornament '
        'tremolo voice 1'
    ) == ['accidental:isis']
