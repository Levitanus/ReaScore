from typing import List
from reapy_boost.core.item.midi_event import MIDIEventDict
from rea_score.primitives import (
    Attachment, Event, NotationEvent, NotationMarker, TimeSignature
)
from rea_score.scale import Key, Scale


class NotationKeySignature(NotationMarker, Attachment):

    def __init__(self, key: Key) -> None:
        self.key = key

    def update(self, new: 'NotationEvent') -> bool:
        if not isinstance(new, NotationKeySignature):
            return False
        self.key = new.key
        return True

    def ly_render(self) -> str:
        return self.key.ly_render()

    def for_marker(self) -> str:
        return f'key:{self.key.as_str()}'

    @classmethod
    def from_marker(cls, string: str) -> 'NotationKeySignature':
        _, tonic, scale = string.split(':')
        return NotationKeySignature(Key(tonic, Scale(scale)))

    def apply_to_event(self, event: 'Event') -> None:
        event.prefix.append(self)


class NotationTimeSignature(NotationEvent, Attachment):

    def __init__(self, time_sig: TimeSignature) -> None:
        self.time_sig = time_sig

    def update(self, new: 'NotationEvent') -> bool:
        if not isinstance(new, NotationTimeSignature):
            return False
        self.time_sig = new.time_sig
        return True

    def ly_render(self) -> str:
        return self.time_sig.ly_render()

    def apply_to_event(self, event: 'Event') -> None:
        event.prefix.append(self)


class NotationText(NotationEvent, Attachment):

    def __init__(self, text: str) -> None:
        self.text = text

    def apply_to_event(self, event: Event) -> None:
        event.postfix.append(self)

    def ly_render(self) -> str:
        return f'^\\markup "{self.text}"'

    def update(self, new: NotationEvent) -> bool:
        if not isinstance(new, self.__class__):
            return False
        super().update(new)
        self.text = new.text
        return True

    @classmethod
    def is_text_event(cls, event: MIDIEventDict) -> bool:
        if (event['buf'][0]) != 0xff:
            return False
        # print(event['buf'][0:2], 0 < event['buf'][1] < 15)
        if 0 < event['buf'][1] < 15:
            return True
        return False

    @classmethod
    def from_midibuf(cls, buf: List[int]) -> 'NotationText':
        text = bytes(buf[2:]).decode('latin-1')
        return NotationText(text)

    def __repr__(self) -> str:
        return f'<NotationText "{self.text}">'

class NotationPlainText(NotationEvent, Attachment):

    def __init__(self, text: str) -> None:
        self.text = text

    def update(self, new: 'NotationEvent') -> bool:
        if not isinstance(new, NotationPlainText):
            return False
        self.text = new.text
        return True

    def ly_render(self) -> str:
        return self.text

    def apply_to_event(self, event: 'Event') -> None:
        event.prefix.append(self)