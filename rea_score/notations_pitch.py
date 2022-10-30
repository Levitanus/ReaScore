from enum import Enum
from typing import Optional
from rea_score.primitives import (ALPHABET, PITCH_IS_SPACER, Attachment, Clef,
                                  Event, GraceType, NotationEvent,
                                  NotationPitch, Pitch, TupletRate)
from rea_score.scale import Accidental
import reapy_boost as rpr


class NotationAccidental(NotationPitch, token='accidental'):

    def __init__(self, pitch: Pitch, accidental: Accidental) -> None:
        super().__init__(pitch)
        self.accidental = accidental

    def apply_to_event(self, event: Event) -> None:
        event.pitch.accidental = self.accidental

    @property
    def for_midi(self) -> str:
        return 'accidental:' + self.accidental.to_str()

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationAccidental':
        return NotationAccidental(pitch,
                                  Accidental.from_str(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.accidental = new.accidental
        return True

    def __repr__(self) -> str:
        return '<NotationAccidental {}, accidental:{}>'.format(
            self.pitch, self.accidental.to_str())


class NotationVoice(NotationPitch, token='voice'):

    def __init__(self, pitch: Pitch, voice: int) -> None:
        super().__init__(pitch)
        self.voice = voice

    def apply_to_event(self, event: Event) -> None:
        event.voice_nr = self.voice

    @property
    def for_midi(self) -> str:
        return f'voice:{self.voice}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationVoice':
        return NotationVoice(pitch, int(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.voice = new.voice
        return True

    def __repr__(self) -> str:
        return f'<NotationVoice {self.pitch}, voice:{self.voice}>'


class NotationStaff(NotationPitch, token='staff'):

    def __init__(self, pitch: Pitch, staff: int) -> None:
        super().__init__(pitch)
        self.staff = staff

    def apply_to_event(self, event: Event) -> None:
        event.staff_nr = self.staff

    @property
    def for_midi(self) -> str:
        return f'staff:{self.staff}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationStaff':
        return NotationStaff(pitch, int(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.staff = new.staff
        return True

    def __repr__(self) -> str:
        return f'<NotationStaff {self.pitch}, staff:{self.staff}>'


class NotationStaffChange(NotationPitch, Attachment, token='staff_change'):

    def __init__(self, pitch: Pitch, staff: int) -> None:
        super().__init__(pitch)
        self.staff = staff

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return f'\\change Staff = "Staff{ALPHABET[self.staff]}"'

    @property
    def for_midi(self) -> str:
        return f'staff_change:{self.staff}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationStaffChange':
        return NotationStaffChange(pitch, int(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.staff = new.staff
        return True

    def __repr__(self) -> str:
        return f'<NotationStaffChange {self.pitch}, staff_change:{self.staff}>'


class NotationClef(NotationPitch, token='clef'):

    def __init__(self, pitch: Pitch, clef: Clef) -> None:
        super().__init__(pitch)
        self.clef = clef

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self.clef)

    @property
    def for_midi(self) -> str:
        return f'clef:{self.clef.value}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationClef':
        return NotationClef(pitch, Clef(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.clef = new.clef
        return True

    def __repr__(self) -> str:
        return f'<NotationClef {self.pitch}, clef:{self.clef}>'


class NotationGhost(NotationPitch, Attachment, token='ghost'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return '\\parenthesize'

    @property
    def for_midi(self) -> str:
        return f'ghost'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationGhost':
        return NotationGhost(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationGhost {self.pitch}>'


class NotationTrill(NotationPitch, Attachment, token='trill'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return '\\trill'

    @property
    def for_midi(self) -> str:
        return f'trill'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationTrill':
        return NotationTrill(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationTrill {self.pitch}>'


class NotationBreakBefore(NotationPitch, Attachment, token='break_before'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return '\\break'

    @property
    def for_midi(self) -> str:
        return f'break_before'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationBreakBefore':
        return NotationBreakBefore(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationBreakBefore {self.pitch}>'


class NotationTrem(NotationPitch, token='trem'):

    def __init__(self, pitch: Pitch, trem_denom: int) -> None:
        super().__init__(pitch)
        self.trem_denom = trem_denom

    def apply_to_event(self, event: Event) -> None:
        event.length.trem_denom = self.trem_denom

    def ly_render(self) -> str:
        return f':{self.trem_denom}'

    @property
    def for_midi(self) -> str:
        return f'trem:{self.trem_denom}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationTrem':
        return NotationTrem(pitch, int(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.trem_denom = new.trem_denom
        return True

    def __repr__(self) -> str:
        return f'<NotationTrem {self.pitch}, {self.trem_denom}>'


class NotationIgnore(NotationPitch, token='ignore'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NotationIgnore):
            return self.pitch == other.pitch
        return False

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    @property
    def for_midi(self) -> str:
        return f'ignore'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationIgnore':
        return NotationIgnore(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationIgnore {self.pitch}>'


class NotationUnnormalizedLength(NotationPitch, token='unnormalized'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NotationUnnormalizedLength):
            return self.pitch == other.pitch
        return False

    def apply_to_event(self, event: Event) -> None:
        event.unnormalized = True

    @property
    def for_midi(self) -> str:
        return f'unnormalized'

    @classmethod
    def from_midi(cls, pitch: Pitch,
                  string: str) -> 'NotationUnnormalizedLength':
        return NotationUnnormalizedLength(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationUnnormalizedLength {self.pitch}>'


class NotationSpacer(NotationPitch, token='spacer'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NotationSpacer):
            return self.pitch == other.pitch
        return False

    def apply_to_event(self, event: Event) -> None:
        event.pitch.midi_pitch = PITCH_IS_SPACER

    @property
    def for_midi(self) -> str:
        return f'spacer'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationSpacer':
        return NotationSpacer(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationSpacer {self.pitch}>'


class NotationTupletBegin(NotationPitch, Attachment, token='tuplet_begin'):

    def __init__(self, pitch: Pitch, rate: TupletRate) -> None:
        super().__init__(pitch)
        self.rate = rate

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return f'\\tuplet {self.rate.to_str()}{{'

    @property
    def for_midi(self) -> str:
        return f'tuplet_begin:{self.rate.to_str()}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationTupletBegin':
        return NotationTupletBegin(pitch,
                                   TupletRate.from_str(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.tuplet = new.tuplet
        return True

    def __repr__(self) -> str:
        return f'<NotationTupletBegin {self.pitch}, tuplet:{self.rate}>'


class NotationTupletEnd(NotationPitch, Attachment, token='tuplet_end'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'}}'

    @property
    def for_midi(self) -> str:
        return f'tuplet_end'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationTupletEnd':
        return NotationTupletEnd(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationTupletEnd {self.pitch}>'


class NotationGraceBegin(NotationPitch, Attachment, token='grace_begin'):

    def __init__(self,
                 pitch: Pitch,
                 grace_type: GraceType = GraceType.grace) -> None:
        super().__init__(pitch)
        self.grace_type = grace_type

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return f'\\{self.grace_type.value}{{'

    @property
    def for_midi(self) -> str:
        return f'grace_begin:{self.grace_type.value}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationGraceBegin':
        return NotationGraceBegin(pitch, GraceType(string.split(':')[1]))

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.grace_type = new.grace_type
        return True

    def __repr__(self) -> str:
        return f'<NotationGraceBegin {self.pitch}, grace_type:{self.grace_type}>'


class NotationGraceEnd(NotationPitch, Attachment, token='grace_end'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'}}'

    @property
    def for_midi(self) -> str:
        return f'grace_end'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationGraceEnd':
        return NotationGraceEnd(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationGraceEnd {self.pitch}>'


class NotationDynamics(NotationPitch, Attachment, token='dyn'):

    def __init__(self, pitch: Pitch, dynamics: str) -> None:
        super().__init__(pitch)
        self.dynamics = dynamics

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'\\{self.dynamics}'

    @property
    def for_midi(self) -> str:
        return f'dyn:{self.dynamics}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationDynamics':
        return NotationDynamics(pitch, string.split(':')[1])

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.dynamics = new.dynamics
        return True

    def __repr__(self) -> str:
        return f'<NotationDynamics {self.pitch}, dyn:{self.dynamics}>'


class NotationXNoteBegin(NotationPitch, Attachment, token='x_begin'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return f'\\xNote{{'

    @property
    def for_midi(self) -> str:
        return f'x_begin'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationXNoteBegin':
        return NotationXNoteBegin(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        return True

    def __repr__(self) -> str:
        return f'<NotationXNoteBegin {self.pitch}>'


class NotationXNoteEnd(NotationPitch, Attachment, token='x_end'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'}}'

    @property
    def for_midi(self) -> str:
        return f'x_end'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationXNoteEnd':
        return NotationXNoteEnd(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationXNoteEnd {self.pitch}>'


class NotationBeamGroupBegin(NotationPitch, Attachment, token='beam_begin'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'['

    @property
    def for_midi(self) -> str:
        return f'beam_begin'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationBeamGroupBegin':
        return NotationBeamGroupBegin(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        return True

    def __repr__(self) -> str:
        return f'<NotationBeamGroupBegin {self.pitch}>'


class NotationBeamGroupEnd(NotationPitch, Attachment, token='beam_end'):

    def __init__(self, pitch: Pitch) -> None:
        super().__init__(pitch)

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f']'

    @property
    def for_midi(self) -> str:
        return f'beam_end'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationBeamGroupEnd':
        return NotationBeamGroupEnd(pitch)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        return super().update(new)

    def __repr__(self) -> str:
        return f'<NotationBeamGroupEnd {self.pitch}>'


class NotationArticulation(NotationPitch, Attachment, token='artic'):

    def __init__(self,
                 pitch: Pitch,
                 articulation: str = '',
                 position: str = '-') -> None:
        super().__init__(pitch)
        self.articulation = articulation
        self.position = position

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'{self.position}{self.articulation}'

    @property
    def for_midi(self) -> str:
        return f'artic:{self.articulation}:{self.position}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationArticulation':
        tokens = string.split(':')[1:3]
        return NotationArticulation(pitch, *tokens)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.articulation = new.articulation
        return True

    def __repr__(self) -> str:
        return (f'<NotationArticulation {self.pitch},'
                f' articulation:{self.articulation}>')


class NotationBeaming(NotationPitch, Attachment, token='beaming'):

    def __init__(self, pitch: Pitch, left: str = '', right: str = '') -> None:
        super().__init__(pitch)
        self.left = left
        self.right = right

    def apply_to_event(self, event: Event) -> None:
        event.prefix.append(self)

    def ly_render(self) -> str:
        return (' \once \override Stem.beaming = #(cons '
                f'(list {self.left}) (list {self.right})) ')

    @property
    def for_midi(self) -> str:
        return f'beaming:{self.left}:{self.right}'

    @classmethod
    def from_midi(cls, pitch: Pitch, string: str) -> 'NotationBeaming':
        tokens = string.split(':')[1:3]
        return NotationBeaming(pitch, *tokens)

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.left = new.left
        return True

    def __repr__(self) -> str:
        return (f'<NotationBeaming {self.pitch},'
                f' left:{self.left},  right:{self.right}>')
