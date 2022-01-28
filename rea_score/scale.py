from enum import Enum, auto
import re
from typing import Dict, List, Optional
import warnings


class Accidental(Enum):
    is_ = auto()
    isis = auto()
    es = auto()
    eses = auto()
    white = auto()

    @classmethod
    def from_str(cls, string: str) -> 'Accidental':
        if not string:
            return cls.white
        replacements = {'♯': 'is', '♭': 'es', re.compile(r'\bis\b'): 'is_'}
        for pattern, repl in replacements.items():
            string = re.sub(pattern, repl, string)  # type:ignore
        return getattr(cls, string)  # type:ignore


class Key:

    def __init__(self, tonic: str, scale: 'Scale') -> None:
        tonic = tonic.lower()
        replacements = {'is': '♯', 'es': '♭', 's': '♭'}
        for pattern, repl in replacements.items():
            tonic = re.sub(pattern, repl, tonic)
        self.tonic = tonic
        self.scale = scale

    @property
    def for_librosa(self) -> str:
        return f'{self.tonic}:{self.scale.for_librosa}'

    @property
    def tonic_for_ly(self) -> str:
        return self.tonic.replace('♭', 'es').replace('♯', 'is')

    def ly_render(self) -> str:
        return f'\\key {self.tonic_for_ly} \\{self.scale.value}'

    def __repr__(self) -> str:
        return f'<Key {self.tonic}:{self.scale.value}>'


class Scale(Enum):
    major = 'major'
    minor = 'minor'
    dorian = 'dorian'
    phrygian = 'phrygian'
    lydian = 'lydian'
    mixolydian = 'mixolydian'
    locrian = 'locrian'

    @property
    def for_librosa(self) -> str:
        return self.value[:3]


class PitchResolver:

    scale_structure = {
        Scale.major: [2, 2, 1, 2, 2, 2],
        Scale.minor: [2, 1, 2, 2, 1, 2],
        Scale.dorian: [2, 1, 2, 2, 2, 1],
        Scale.phrygian: [1, 2, 2, 2, 1, 2],
        Scale.lydian: [2, 2, 2, 1, 2, 2],
        Scale.mixolydian: [2, 2, 1, 2, 2, 1],
        Scale.locrian: [1, 2, 2, 1, 2, 2],
    }

    nr_of_note = {
        'b♯': 0,
        'c': 0,
        'd♭♭': 0,
        'b♯♯': 1,
        'c♯': 1,
        'd♭': 1,
        'c♯♯': 2,
        'd': 2,
        'e♭♭': 2,
        'd♯': 3,
        'e♭': 3,
        'd♯♯': 4,
        'e': 4,
        'f♭': 4,
        'e♯': 5,
        'f': 5,
        'g♭♭': 5,
        'e♯♯': 6,
        'f♯': 6,
        'g♭': 6,
        'f♯♯': 7,
        'g': 7,
        'a♭♭': 7,
        'g♯': 8,
        'a♭': 8,
        'g♯♯': 9,
        'a': 9,
        'b♭♭': 9,
        'a♯': 10,
        'b♭': 10,
        'c♭♭': 10,
        'a♯♯': 11,
        'b': 11,
        'c♭': 11,
    }

    note_of_nr: Dict[int, List[str]] = {}
    for note, nr in nr_of_note.items():
        if not nr in note_of_nr:
            note_of_nr[nr] = []
        note_of_nr[nr].append(note)

    natural_note = {'c': 0, 'd': 1, 'e': 2, 'f': 3, 'g': 4, 'a': 5, 'b': 6}
    natural_number = {val: key for key, val in natural_note.items()}

    @classmethod
    def midi_to_note(
        cls,
        midi: int,
        key: Key,
        accidental: Optional[Accidental] = None
    ) -> str:
        octave = midi // 12 - 1
        midi = midi % 12
        if accidental is not None:
            try:
                return cls._with_octave(
                    ENHARM_ACC[midi][accidental].lower(), octave
                )
            except KeyError:
                pass  # Because we will do it the long way
        key_midi = cls.nr_of_note[key.tonic]
        root_idx = cls.natural_note[key.tonic[0]]
        optimized_scale: List[int] = [key_midi]
        string_scale = [key.tonic]
        used_acc_list: List[str] = []
        for idx, interval in enumerate(cls.scale_structure[key.scale]):
            sum_ = optimized_scale[idx]
            sum_ += interval
            if sum_ > 11:
                sum_ %= 12
            current_note = string_scale[idx]
            note_idx = cls.natural_note[current_note[0]]
            next_note = cls.get_accidental_of_next_note(note_idx, sum_)
            string_scale.append(next_note)
            optimized_scale.append(sum_)
            if len(next_note) > 1:
                used_acc_list.append(next_note[1])
        used_acc = set(used_acc_list)
        try:
            # print('note from scale')
            final = string_scale[optimized_scale.index(midi)]
        except ValueError:
            # print(midi, key_midi)
            if midi == key_midi + 1 and key.scale is Scale.minor:
                # print('minor II♭')
                final = cls.get_accidental_of_next_note(root_idx, midi)
            elif midi == (key_midi + 8) % 12 and key.scale is Scale.major:
                # print('major VI♭')
                # print(f'key root: {cls.natural_number[root_idx]}')
                final = cls.get_accidental_of_next_note(
                    (root_idx + 4) % 7, midi
                )
            else:
                # print('regular')
                acc_found = None if not used_acc else used_acc.pop()
                final = cls.get_accidental_of_midi(acc_found, midi)
        # print(midi, key, optimized_scale, string_scale)
        return cls._with_octave(final, octave)

    @classmethod
    def _with_octave(cls, pitch: str, octave: int) -> str:
        if 'b♯' in pitch:
            octave -= 1
        if 'c♭' in pitch:
            octave += 1
        return pitch + str(octave)

    @classmethod
    def get_accidental_of_midi(
        cls, accidental: Optional[str], midi: int
    ) -> str:
        notes = cls.note_of_nr[midi]
        acc = accidental if accidental else '♯'
        for note in notes:
            if re.match(r'\w' + re.escape(acc) + r'$', note):
                return note
        if accidental is None:
            return ENHARM_ACC[midi][Accidental.white].lower()
        warnings.warn(
            "Can't Find proper accidental for accidental:{}, midi:{}".format(
                accidental, midi
            )
        )
        return ENHARM_ACC[midi][Accidental.white].lower()
        # raise ValueError(
        #     "Can't Find proper accidental for accidental:{}, midi:{}".format(
        #         accidental, midi
        #     )
        # )

    @classmethod
    def get_accidental_of_next_note(cls, root_idx: int, midi: int) -> str:
        note_idx = root_idx + 1
        if note_idx > 6:
            note_idx = 0
        current_note = cls.natural_number[note_idx]
        notes = cls.note_of_nr[midi]
        for note in notes:
            if current_note in note:
                return note
        raise ValueError(
            "Can't Find proper accidental for root_idx:{}, midi:{}".format(
                root_idx, midi
            )
        )


def midi_to_note(
    midi: int, key: Key, accidental: Optional[Accidental] = None
) -> str:
    return PitchResolver.midi_to_note(midi, key, accidental)


ENHARM_ACC = {
    0: {
        Accidental.white: 'C',
        Accidental.is_: 'B♯',
        Accidental.eses: 'D♭♭'
    },
    1: {
        Accidental.is_: 'C♯',
        Accidental.isis: 'B♯♯',
        Accidental.es: 'D♭'
    },
    2: {
        Accidental.white: 'D',
        Accidental.isis: 'C♯♯',
        Accidental.eses: 'E♭♭'
    },
    3: {
        Accidental.is_: 'D♯',
        Accidental.es: 'E♭',
        Accidental.eses: 'F♭♭',
    },
    4: {
        Accidental.white: 'E',
        Accidental.isis: 'D♯♯',
        Accidental.es: 'F♭'
    },
    5: {
        Accidental.white: 'F',
        Accidental.is_: 'E♯',
        Accidental.eses: 'G♭♭'
    },
    6: {
        Accidental.is_: 'F♯',
        Accidental.isis: 'E♯♯',
        Accidental.es: 'G♭',
    },
    7: {
        Accidental.white: 'G',
        Accidental.isis: 'F♯♯',
        Accidental.eses: 'A♭♭'
    },
    8: {
        Accidental.is_: 'G♯',
        Accidental.es: 'A♭'
    },
    9: {
        Accidental.white: 'A',
        Accidental.isis: 'G♯♯',
        Accidental.eses: 'B♭♭'
    },
    10: {
        Accidental.is_: 'A♯',
        Accidental.es: 'B♭',
        Accidental.eses: 'C♭♭'
    },
    11: {
        Accidental.white: 'B',
        Accidental.isis: 'A♯♯',
        Accidental.es: 'C♭'
    },
}
