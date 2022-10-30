from copy import deepcopy
from enum import Enum, auto
from fractions import Fraction
from pprint import pformat
import re
import typing as ty
import warnings
# import librosa
import reapy_boost as rpr
from reapy_boost import reascript_api as RPR
from reapy_boost.core.item.midi_event import MIDIEventDict

from .scale import Accidental, ENHARM_ACC, Scale, midi_to_note, Key

LIMIT_DENOMINATOR = 128
PITCH_IS_CHORD = 12800
PITCH_IS_TUPLET = 12801
PITCH_IS_VOICESPLIT = 12802
PITCH_IS_GRACE = 12803
PITCH_IS_SPACER = 12804
ROUND_QUARTERS = 4

ALPHABET: ty.Dict[int, str] = {
    1: 'A',
    2: 'B',
    3: 'C',
    4: 'D',
    5: 'E',
    6: 'F',
    7: 'G',
    8: 'H',
    9: 'I'
}


class Fractured:

    @property
    def fraction(self) -> Fraction:
        raise NotImplementedError()

    @classmethod
    def power_of_two(cls, target: int) -> int:
        if target > 1:
            for i in range(1, int(target)):
                if (2**i >= target):
                    return ty.cast(int, 2**(i - 1))
        elif target in (1, 0):
            return target
        raise ValueError(f"can't resolve numerator: {target}")

    @classmethod
    def closest_power_of_two(cls, target: int) -> int:
        if target >= 2:
            for i in range(int(target)):
                if 2**i == target:
                    return 2**i
                if 2**i > target:
                    return ty.cast(int, 2**(i - 1))
        elif target in (0, 1):
            return target
        raise ValueError(f"can't resolve target: {target}")

    @classmethod
    def normalized(
        cls, fraction: Fraction, head: ty.Tuple[Fraction, ...] = tuple()
    ) -> ty.Tuple[Fraction, ...]:
        num = fraction.numerator
        den = fraction.denominator

        if den == 1 or num < 5:
            return fraction,
        if num == cls.power_of_two(num):
            return fraction,
        num_nr = cls.power_of_two(num)
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
        # print(self, other, ':', first, last)
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
        self.trem_denom = 0
        self.bar_multiplier = 0

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.length / 4).limit_denominator(LIMIT_DENOMINATOR)

    @staticmethod
    def from_fraction(frac: ty.Union[Fraction, float]) -> 'Length':
        return Length(float(frac) * 4)

    def __repr__(self) -> str:
        return f'<Length {self.fraction}{" full-bar" if self.full_bar else ""}>'


class Pitch:

    def __init__(
        self,
        midi_pitch: ty.Optional[int] = None,
        accidental: ty.Optional[Accidental] = None,
        tie: bool = False,
        note_name: str = '',
    ) -> None:
        self.midi_pitch = midi_pitch
        self.accidental = accidental
        self.tie = tie
        self.note_name = note_name

    def named_pitch(self, key: Key = Key('C', Scale.major)) -> str:
        if self.midi_pitch is None:
            return 'r'
        if self.midi_pitch is PITCH_IS_SPACER:
            return 's'
        if self.midi_pitch == PITCH_IS_CHORD:
            return 'PITCH_IS_CHORD'
        if self.note_name:
            return self.note_name
        return midi_to_note(self.midi_pitch, key, self.accidental)

    def __repr__(self) -> str:
        if self.midi_pitch is None:
            return '<Pitch is rest>'
        if self.midi_pitch is PITCH_IS_SPACER:
            return '<Pitch is spacer>'
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


class Clef(Attachment, Enum):
    bass = 'bass'
    treble = 'treble'
    alto = 'alto'
    tenor = 'tenor'
    percussion = "percussion"

    GG = "GG"
    french = "french"
    soprano = "soprano"
    mezzosoprano = "mezzosoprano"
    baritone = "baritone"
    altovarC = "altovarC"
    tenorvarC = "tenorvarC"
    subbass = "subbass"

    def ly_render(self) -> str:
        return f'\\clef {self.value}'


class TimeSignature(Attachment):

    def __init__(self, numerator: int, denomenator: int) -> None:
        self.numerator, self.denomenator = numerator, denomenator

    def ly_render(self) -> str:
        return f"\\time {self.numerator}/{self.denomenator}"


class NotationEvent:

    def update(self, new: 'NotationEvent') -> bool:
        return False

    def apply_to_event(self, event: 'Event') -> None:
        raise NotImplementedError()

    def ly_render(self) -> str:
        raise NotImplementedError()


class GlobalNotationEvent:

    def __init__(self, events: ty.List[NotationEvent]) -> None:
        self.events = events

    def ly_render(self) -> str:
        return ' '.join(ev.ly_render() for ev in self.events)


class NotationMarker(NotationEvent):

    def for_marker(self) -> str:
        raise NotImplementedError()

    @classmethod
    def from_marker(cls, string: str) -> 'NotationMarker':
        raise NotImplementedError()

    @classmethod
    def reascore_tokens(cls, string: str) -> ty.List[str]:
        tokens = re.search(r'#ReaScore\s(\S+)', string)
        if not tokens:
            return []
        return tokens.groups()[0].split('|')

    @classmethod
    def from_reaper_marker(cls, string: str) -> ty.List['NotationMarker']:
        tokens = cls.reascore_tokens(string)
        if not tokens:
            return []
        notations = []
        for token in tokens:
            if token.startswith('key'):
                notations.append(NotationKeySignature.from_marker(token))
        return notations

    @classmethod
    def to_reaper_marker(cls, events: ty.List['NotationMarker']) -> str:
        tokens = []
        for event in events:
            tokens.append(event.for_marker())
        return '#ReaScore {}'.format('|'.join(tokens))


class NotationPitch(NotationEvent):

    _tokens: ty.Dict[str, ty.Type['NotationPitch']] = {}

    def __init_subclass__(cls, token: str) -> None:
        NotationPitch._tokens[token] = cls

    def __init__(self, pitch: Pitch) -> None:
        super().__init__()
        self.pitch = pitch

    @property
    def for_midi(self) -> str:
        raise NotImplementedError()

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationPitch':
        raise NotImplementedError()

    def update(self, new: 'NotationEvent') -> bool:
        if not isinstance(new, NotationPitch):
            return False
        if self.pitch != new.pitch:
            warnings.warn(
                'Pitches are not equal! {} replaced with {}'.format(
                    self.pitch, new.pitch
                )
            )
        return True

    @classmethod
    def is_reascore_event(cls, event: MIDIEventDict) -> bool:
        if (event['buf'][0:2]) != [0xff, 0x0f]:
            return False
        return cls.is_reascore_event_buf(event['buf'])

    @classmethod
    def from_token(cls, token: str,
                   pitch: Pitch) -> ty.Optional['NotationPitch']:
        token_orig = token
        token = token.split(':')[0]
        if token in cls._tokens:
            return cls._tokens[token].from_midi(pitch, token_orig)
        # if token.startswith('accidental'):
        #     return NotationAccidental.from_midi(pitch, token)
        # if token.startswith('voice'):
        #     return NotationVoice.from_midi(pitch, token)
        # if token.startswith('staff'):
        #     return NotationStaff.from_midi(pitch, token)
        # if token.startswith('clef'):
        #     return NotationClef.from_midi(pitch, token)
        # if token.startswith('ghost'):
        #     return NotationGhost.from_midi(pitch, token)
        # if token.startswith('trill'):
        #     return NotationTrill.from_midi(pitch, token)
        # if token.startswith('trem'):
        #     return NotationTrem.from_midi(pitch, token)
        # if token.startswith('ignore'):
        #     return NotationIgnore.from_midi(pitch, token)
        return None

    @classmethod
    def reascore_tokens(cls, string: str) -> ty.List[str]:
        tokens = re.search(r'\stext\s(ReaScore\S+)', string)
        if not tokens:
            return []
        return tokens.groups()[0].split('|')

    @classmethod
    def is_reascore_event_buf(cls, buf: ty.List[int]) -> bool:
        string = bytes(buf[2:]).decode('latin-1')
        # print(string)
        if not string.startswith('NOTE'):
            return False
        if cls.reascore_tokens(string):
            return True
        return False

    @classmethod
    def from_midibuf(cls, buf: ty.List[int]) -> ty.List['NotationPitch']:
        string = bytes(buf[2:]).decode('latin-1')
        if not NotationPitch.is_reascore_event_buf(buf):
            raise ValueError(f'Not a ReaScore notation event: {string}')
        print(string)
        tokens = cls.reascore_tokens(string)
        if m := re.match(r'NOTE\s\d+\s(\d+)', string):
            pitch = Pitch(int(m.groups()[0]))
        else:
            raise ValueError(f'Can not get pitch from string: {string}')
        events = []
        print(tokens, pitch)
        for token in tokens[1:]:
            event = NotationPitch.from_token(token, pitch)
            if event is not None:
                events.append(event)
            print(token, event)
        return events

    @classmethod
    def to_midi_buf(
        cls,
        events: ty.List['NotationPitch'],
        check_pitch: ty.Optional[Pitch] = None,
        channel: int = 0,
        original_buf: ty.Optional[ty.List[int]] = None,
    ) -> ty.List[int]:
        pitch = ty.cast(Pitch, check_pitch)
        tokens = []
        if len(events) == 0:
            raise ValueError('can note pack empty list')
        for event in events:
            tokens.append(event.for_midi)
            if event.pitch is None:
                raise ValueError("only pitched notation supported")
            if pitch != event.pitch:
                raise ValueError(
                    """Notations for different pitches has to \
                    be packed separatelly."""
                )
            pitch = event.pitch
        tokens_str = f" text ReaScore|{'|'.join(tokens)}"
        if original_buf:
            string = bytes(original_buf[2:]).decode('latin-1')
            original_tokens = '|'.join(cls.reascore_tokens(string))
            if original_tokens:
                string = re.sub(
                    f'text ReaScore|{original_tokens}', tokens_str, string
                )
            else:
                string += tokens_str
        else:
            string = f"NOTE {channel} {pitch.midi_pitch}{tokens_str}"
        return [
            0xff,
            0x0f,
            *list(string.encode('latin-1')),
        ]


class Event:

    def __init__(
        self,
        length: Length,
        pitch: Pitch = Pitch(None),
        voice_nr: int = 1,
        staff_nr: int = 1,
        prefix: ty.Optional[ty.List[Attachment]] = None,
        postfix: ty.Optional[ty.List[Attachment]] = None,
    ) -> None:
        (
            self.length, self.pitch, self.voice_nr, self.staff_nr, self.prefix,
            self.postfix
        ) = (
            length, pitch, voice_nr, staff_nr, prefix if prefix else [],
            postfix if postfix else []
        )
        self.unnormalized = False

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, int, ty.List[Attachment],
                  ty.List[Attachment]]:
        return (
            self.length,
            self.pitch,
            self.voice_nr,
            self.staff_nr,
            self.prefix,
            self.postfix,
        )

    def __repr__(self) -> str:
        return f"<Event {self._params}>"

    def make_chord(self) -> 'Chord':
        chord =  Chord(*self._params, pitches=[self.pitch])
        chord.unnormalized = self.unnormalized
        return chord

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
        right.prefix = []
        left.postfix = []
        support_tie = False
        if self.pitch.midi_pitch is not None:
            support_tie = True
        if tie and support_tie:
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
        staff_nr: int = 1,
        prefix: ty.Optional[ty.List[Attachment]] = None,
        postfix: ty.Optional[ty.List[Attachment]] = None,
        pitches: ty.List[Pitch] = None,  # type:ignore
    ) -> None:
        super().__init__(
            length,
            Pitch(PITCH_IS_CHORD),
            voice_nr,
            staff_nr,
            prefix,
            postfix,
        )
        if not pitches:
            raise ValueError("pitches must be specified")
        self.pitches = pitches

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, int, ty.List[Attachment],
                  ty.List[Attachment], ty.List[Pitch]]:
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


class TupletRate:

    def __init__(self, numerator: int, denominator: int) -> None:
        self.numerator = numerator
        self.denominator = denominator

    @staticmethod
    def from_str(string: str) -> 'TupletRate':
        return TupletRate(*(int(s) for s in string.split('/')))

    def to_str(self) -> str:
        return f'{self.numerator}/{self.denominator}'

    def __repr__(self) -> str:
        return f"<TupletRate {self.to_str()}>"


class Tuplet(Event):

    def __init__(
        self,
        length: Length,
        pitch: ty.Optional[Pitch] = None,
        voice_nr: int = 1,
        staff_nr: int = 1,
        prefix: ty.Optional[ty.List[Attachment]] = None,
        postfix: ty.Optional[ty.List[Attachment]] = None,
        rate: TupletRate = TupletRate(3, 2),
        events: ty.Optional[ty.List[Event]] = None,
    ) -> None:
        super().__init__(
            length,
            Pitch(PITCH_IS_TUPLET),
            voice_nr,
            staff_nr,
            prefix,
            postfix,
        )
        self._rate = rate
        if events is None:
            events = []
        self._events = events

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, int, ty.List[Attachment],
                  ty.List[Attachment], TupletRate, ty.List[Event]]:
        return (*super()._params, self.rate, self.events)

    def __repr__(self) -> str:
        return f"<Tuplet {self.rate.to_str()} {pformat(self._params, indent=4)}>"

    @property
    def rate(self) -> TupletRate:
        real, truncated = Fraction(0), Fraction(0)
        for event in self._events:
            fraction = event.length.fraction
            real = (real + fraction).limit_denominator(LIMIT_DENOMINATOR)
            truncated += Fraction(
                fraction.numerator /
                Fractured.closest_power_of_two(fraction.denominator)
            ).limit_denominator(LIMIT_DENOMINATOR)
        # print(real, truncated)
        rate = Fraction(real / truncated).limit_denominator(LIMIT_DENOMINATOR)
        self._rate = TupletRate(rate.denominator, rate.numerator)
        return self._rate

    @property
    def events(self) -> ty.List[Event]:
        out = []
        for event in self._events:
            ev = deepcopy(event)
            fraction = ev.length.fraction
            denom = Fractured.closest_power_of_two(fraction.denominator)
            ev.length = Length.from_fraction(
                Fraction(fraction.numerator / denom)
            )
            out.append(ev)
        return out

    def append(self, event: Event) -> None:
        if event.length == 0:
            return
        self.postfix = event.postfix  # should be used extend instead?
        self._events.append(event)
        self.length.length += event.length.length


class GraceType(Enum):
    grace = 'grace'
    acciaccatura = 'acciaccatura'
    appoggiatura = 'appoggiatura'
    slashedGrace = 'slashedGrace'


class Grace(Event, Attachment):

    def __init__(
        self,
        length: Length = Length(0),
        pitch: ty.Optional[Pitch] = None,
        voice_nr: int = 1,
        staff_nr: int = 1,
        prefix: ty.Optional[ty.List[Attachment]] = None,
        postfix: ty.Optional[ty.List[Attachment]] = None,
        grace_type: GraceType = GraceType.grace,
        events: ty.Optional[ty.List[Event]] = None,
    ) -> None:
        super().__init__(
            length,
            Pitch(PITCH_IS_GRACE),
            voice_nr,
            staff_nr,
            prefix,
            postfix,
        )
        self.grace_type = grace_type
        self._events = events or []

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, int, ty.List[Attachment],
                  ty.List[Attachment], GraceType, ty.List[Event]]:
        return (*super()._params, self.grace_type, self.events)

    def __repr__(self) -> str:
        return f"<Grace {self.grace_type} {pformat(self._params, indent=4)}>"

    def append(self, event: Event) -> None:
        if event.length == 0:
            return
        # self.postfix = event.postfix  # should be used extend instead?
        self._events.append(event)

    @property
    def events(self) -> ty.List[Event]:
        return self._events


class VoiceSplit(Event):

    def __init__(
        self,
        length: Length,
        pitch: ty.Optional[Pitch] = None,
        voice_nr: int = 1,
        staff_nr: int = 1,
        prefix: ty.Optional[ty.List[Attachment]] = None,
        postfix: ty.Optional[ty.List[Attachment]] = None,
        event_lists: ty.Optional[ty.List[ty.List[Event]]] = None,
    ) -> None:
        super().__init__(
            length,
            Pitch(PITCH_IS_TUPLET),
            voice_nr,
            staff_nr,
            prefix,
            postfix,
        )
        if event_lists is None:
            event_lists = []
        self._event_lists = event_lists

    @property
    def _params(
        self
    ) -> ty.Tuple[Length, Pitch, int, int, ty.List[Attachment],
                  ty.List[Attachment], ty.List[Event]]:
        return (*super()._params, self.events)

    def __repr__(self) -> str:
        return f"<VoiceSplit {pformat(self._params, indent=4)}>"

    @property
    def events(self) -> ty.List[Event]:
        return zip(self._events_lists)
