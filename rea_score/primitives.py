from copy import deepcopy
from enum import Enum, auto
from fractions import Fraction
from pprint import pformat
import typing as ty
# import librosa
import reapy as rpr
from reapy import reascript_api as RPR

from .scale import Accidental, ENHARM_ACC, Scale, midi_to_note, Key

LIMIT_DENOMINATOR = 128
PITCH_IS_CHORD = 12800
ROUND_QUARTERS = 3


class Fractured:

    @property
    def fraction(self) -> Fraction:
        raise NotImplementedError()

    @classmethod
    def normalized(
        cls, fraction: Fraction, head: ty.Tuple[Fraction, ...] = tuple()
    ) -> ty.Tuple[Fraction, ...]:

        def power_of_two(target: int) -> int:
            if target > 1:
                for i in range(1, int(target)):
                    if (2**i >= target):
                        return ty.cast(int, 2**(i - 1))
            elif target in (1, 0):
                return target
            raise ValueError(f"can't resolve numerator: {target}")

        num = fraction.numerator
        den = fraction.denominator

        if den == 1 or num < 5:
            return fraction,
        if num == power_of_two(num):
            return fraction,
        num_nr = power_of_two(num)
        whole = Fraction(num_nr / den)
        remainder = Fraction((num - num_nr) / den)
        if remainder.numerator > 3:
            return cls.normalized(remainder, head=tuple((*head, whole)))
        return remainder, whole, *head

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Fractured, Fraction, int)):
            return False
        if isinstance(other, Fractured):
            return other.fraction == self.fraction
        return self.fraction == other

    def __gt__(self, other: ty.Union[Fraction, 'Fractured', int]) -> bool:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction > other

    def __ge__(self, other: ty.Union[Fraction, 'Fractured', int]) -> bool:
        return self > other or self == other

    def __lt__(self, other: ty.Union[Fraction, 'Fractured', int]) -> bool:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction < other

    def __le__(self, other: ty.Union[Fraction, 'Fractured', int]) -> bool:
        return self < other or self == other

    def __add__(self, other: ty.Union[Fraction, 'Fractured', int]) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction + other

    def __sub__(self, other: ty.Union[Fraction, 'Fractured', int]) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction - other

    def __mul__(self, other: ty.Union[Fraction, 'Fractured', int]) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction * other

    def __truediv__(
        self, other: ty.Union[Fraction, 'Fractured', int]
    ) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction / other

    def __mod__(self, other: ty.Union[Fraction, 'Fractured', int]) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction % other

    def __floordiv__(self, other: ty.Union[Fraction, 'Fractured', int]) -> int:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction // other

    def __hash__(self) -> int:
        return hash(self.fraction)


class Position(Fractured):

    def __init__(
        self,
        position_beats: ty.Optional[float] = None,
        take_ppq_position: ty.Optional[ty.Tuple[rpr.Take, float]] = None,
        position_sec: ty.Optional[float] = None
    ) -> None:
        if position_beats is not None:
            self.position = round(position_beats, ROUND_QUARTERS)
        elif take_ppq_position is not None:
            take, ppq = take_ppq_position
            self.position = take.ppq_to_beat(ppq)
        elif position_sec is not None:
            self.position = RPR.TimeMap_timeToQN(position_sec)  #type:ignore
        else:
            raise TypeError('At least one argument has to be specified.')
        (self.bar, self._bar_position,
         self._bar_end_distance) = self._get_bar_position(self.position)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.position / 4).limit_denominator(LIMIT_DENOMINATOR)

    @staticmethod
    def from_fraction(frac: ty.Union[Fraction, float]) -> 'Position':
        return Position(float(frac) * 4)

    @property
    def bar_position(self) -> Fraction:
        return Fraction(self._bar_position / 4
                        ).limit_denominator(LIMIT_DENOMINATOR)

    @property
    def bar_position_norm(self) -> ty.Tuple[Fraction, ...]:
        return tuple(reversed(self.normalized(self.bar_position)))

    @property
    def bar_end_distance(self) -> Fraction:
        return Fraction(self._bar_end_distance / 4
                        ).limit_denominator(LIMIT_DENOMINATOR)

    @property
    def bar_end_distance_qn(self) -> float:
        return self._bar_end_distance

    @staticmethod
    def _get_bar_position(
        position_beats: float
    ) -> ty.Tuple[int, float, float]:
        (
            bar,
            m_start,
            m_end,
        ) = rpr.Project().beats_to_measures(position_beats)
        return bar, position_beats - m_start, m_end - position_beats

    @rpr.inside_reaper()
    def percize_distance(
        self, other: 'Position'
    ) -> ty.Optional[ty.Tuple[ty.Optional['Length'], int,
                              ty.Optional['Length']]]:
        """Get mod distance to other position.

        Parameters
        ----------
        other : Position

        Returns
        -------
        Optional[Tuple[
            Optional[Length]
                distance to the first barline
            int
                distance in full-bars
            Optional[Length]
                distance from the last barline
            ]]
        """
        if self == other:
            return None
        if self > other:
            first = other
            last = self
        else:
            first = self
            last = other
        print(self, other, ':', first, last)
        f_bar, _, f_end = rpr.Project().beats_to_measures(first.position)
        l_bar, l_start, _ = rpr.Project().beats_to_measures(last.position)
        bar: int = l_bar - f_bar
        if bar == 0:
            return Length(last.position - first.position), 0, None
        # if first.bar_position != 0:
        #     bar -= 1
        before: ty.Optional['Length'] = Length(f_end - first.position)
        f_bar_info = rpr.Project().measure_info(f_bar)
        if Length(f_bar_info['end'] - f_bar_info['start']) == before:
            before = None
        after_distance = last.position - l_start
        after = Length(after_distance) if after_distance else None
        return before, bar, after

    def __repr__(self) -> str:
        return '<Position bar:{}, beat:{}, from start:{}>'.format(
            self.bar, self.bar_position, self.position
        )


class Length(Fractured):

    def __init__(self, length_in_beats: float, full_bar: bool = False) -> None:
        self.length = round(length_in_beats, ROUND_QUARTERS)
        self.full_bar = full_bar

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.length / 4).limit_denominator(LIMIT_DENOMINATOR)

    @staticmethod
    def from_fraction(frac: ty.Union[Fraction, float]) -> 'Length':
        return Length(float(frac) * 4)

    def __repr__(self) -> str:
        return f'<Length {self.fraction}{" full-bar" if self.full_bar else ""}>'

    # TODO
    # def bar_position_norm(
    #     self, bar_position_norm: ty.Tuple[Fraction, ...]
    # ) -> ty.Tuple[Fraction, ...]:
    #     if self.fraction > 1:
    #         head = self.fraction // 1


class Pitch:

    def __init__(
        self,
        midi_pitch: ty.Optional[int] = None,
        accidental: ty.Optional[Accidental] = None,
        tie: bool = False,
    ) -> None:
        self.midi_pitch = midi_pitch
        self.accidental = accidental
        self.tie = tie

    def named_pitch(self, key: Key = Key('C', Scale.major)) -> str:
        if self.midi_pitch is None:
            return 'r'
        if self.midi_pitch == PITCH_IS_CHORD:
            return 'PITCH_IS_CHORD'
        return midi_to_note(self.midi_pitch, key, self.accidental)

    def __repr__(self) -> str:
        if self.midi_pitch is None:
            return '<Pitch is rest>'
        if self.midi_pitch == PITCH_IS_CHORD:
            return 'PITCH_IS_CHORD'
        return '<Pitch midi:{}, {} (in c:major), tie={}>'.format(
            self.midi_pitch, self.named_pitch(), self.tie
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pitch):
            return False
        if (self.accidental, self.tie) != (other.accidental, other.tie):
            return False
        return other.midi_pitch == self.midi_pitch

    def __contains__(self, value: object) -> bool:
        if not isinstance(value, Pitch):
            return False
        return value.midi_pitch == self.midi_pitch

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Pitch):
            return False
        if self.midi_pitch is None:
            return False
        if other.midi_pitch is None:
            return False
        return other.midi_pitch < self.midi_pitch

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Pitch):
            return False
        if self.midi_pitch is None:
            return False
        if other.midi_pitch is None:
            return False
        return other.midi_pitch > self.midi_pitch


class Attachment:

    def ly_render(self) -> str:
        raise NotImplementedError()


class Event:

    def __init__(
        self,
        length: Length,
        pitch: Pitch = Pitch(None),
        voice_nr: int = 1,
        preambula: ty.Optional[ty.List[Attachment]] = None,
    ) -> None:
        (self.length, self.pitch, self.voice_nr, self.preambula
         ) = (length, pitch, voice_nr, preambula if preambula else [])

    @property
    def _params(self) -> ty.Tuple[Length, Pitch, int, ty.List[Attachment]]:
        return self.length, self.pitch, self.voice_nr, self.preambula

    def __repr__(self) -> str:
        return f"<Event {self._params}>"

    def make_chord(self) -> 'Chord':
        return Chord(*self._params, pitches=[self.pitch])

    def split(self,
              at_length: Length,
              tie: bool = False) -> ty.Tuple['Event', 'Event']:
        if self.length < at_length:
            raise ValueError(
                'length of event ({}) shorter than argument ({})'.format(
                    self.length, at_length
                )
            )
        left, right = deepcopy(self), deepcopy(self)
        left.length = at_length
        right.length = Length(self.length.length - at_length.length)
        right.preambula = []
        if tie:
            left.pitch.tie = tie
        return left, right

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return False
        return self._params == other._params

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return False
        return self._params > other._params

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return False
        return self._params < other._params


class Chord(Event):

    def __init__(
        self,
        length: Length,
        pitch: ty.Optional[Pitch] = None,
        voice_nr: int = 1,
        preambula: ty.Optional[ty.List[Attachment]] = None,
        pitches: ty.List[Pitch] = None,  # type:ignore
    ) -> None:
        super().__init__(length, Pitch(PITCH_IS_CHORD), voice_nr, preambula)
        if not pitches:
            raise ValueError("pitches must be specified")
        self.pitches = pitches

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, ty.List[Attachment], ty.List[Pitch]]:
        return (*super()._params, self.pitches)

    def __repr__(self) -> str:
        return f"<Chord {pformat(self._params, indent=4)}>"

    def split(self,
              at_length: Length,
              tie: bool = False) -> ty.Tuple['Chord', 'Chord']:
        left, right = ty.cast(ty.Tuple[Chord, Chord], super().split(at_length))
        if tie:
            for pitch in left.pitches:
                pitch.tie = tie
        return left, right

    def append(self, event: Event) -> None:
        if event.length != self.length:
            raise ValueError(
                "event length mismatch: {} != {}".format(
                    event.length, self.length
                )
            )
        if isinstance(event, Chord):
            self.pitches.extend(event.pitches)
        else:
            self.pitches.append(event.pitch)
