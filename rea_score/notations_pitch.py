from rea_score.primitives import Attachment, Clef, Event, NotationEvent, NotationPitch, Pitch, TupletRate
from rea_score.scale import Accidental


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
        return NotationAccidental(
            pitch, Accidental.from_str(string.split(':')[1])
        )

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.accidental = new.accidental
        return True

    def __repr__(self) -> str:
        return '<NotationAccidental {}, accidental:{}>'.format(
            self.pitch, self.accidental.to_str()
        )


# d['accidental'] = NotationAccidental


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


# d['voice'] = NotationVoice


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


# d['staff'] = NotationStaff


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


# d['clef'] = NotationClef


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


# d['ghost'] = NotationGhost


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


# d['trill'] = NotationTrill


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


# d['trem'] = NotationTrem


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


# d['ignore'] = NotationIgnore


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
        return NotationTupletBegin(
            pitch, TupletRate.from_str(string.split(':')[1])
        )

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.tuplet = new.tuplet
        return True

    def __repr__(self) -> str:
        return f'<NotationTupletBegin {self.pitch}, tuplet:{self.rate}>'


# d['tuplet_begin'] = NotationTupletBegin


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


# d['tuplet_end'] = NotationTupletEnd