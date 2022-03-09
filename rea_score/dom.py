from enum import Enum
import re
from typing import Dict, Iterable, Iterator, List, Optional, TypeVar, Union
import reapy_boost as rpr
from reapy_boost.core.item.midi_event import MIDIEventDict

from rea_score.primitives import (
    Attachment, Chord, Clef, Event, GlobalNotationEvent, Length,
    NotationMarker, NotationPitch, NotationEvent, Pitch, Position, Fractured,
    TimeSignature, Tuplet
)
from rea_score.notations_pitch import (
    NotationIgnore, NotationTupletBegin, NotationTupletEnd
)
from rea_score.notation_events import NotationText, NotationTimeSignature

from pprint import pformat, pprint

EventT = TypeVar('EventT', NotationEvent, Event, covariant=True)


class TrackPitchType(Enum):
    default = 'default'
    note_names = 'note_names'


class TrackType(Enum):
    default = 'default'
    drums = 'drums'
    one_line_perc = 'one line perc'
    bongos = 'bongos'


class StaffGroup(Enum):
    GrandStaff = "GrandStaff"
    StaffGroup = "StaffGroup"
    ChoirStaff = "ChoirStaff"
    PianoStaff = "PianoStaff"


class EventPackager:

    def __init__(self, voice: 'Voice', key: Position) -> None:
        self.voice = voice
        self.key = key

    def append(self, event: Event) -> None:
        if event.length == 0:
            return
        if self.key not in self.voice.events:
            if self.key.bar_position == 0:
                barcheck = BarCheck(self.key.bar)
                if self.key.position != 0 and barcheck not in event.prefix:
                    event.prefix.append(barcheck)
            return self.split_by_position(event)
        self.voice.append_to_chord(self.key, event)

    def split_by_position(self, event: Event) -> None:

        if self.key.bar_end_distance < event.length:
            left, append_part = event.split(
                Length(float(self.key.bar_end_distance) * 4), tie=True
            )
        else:
            left = event
        parts = Fractured.normalized(self.key.bar_end_distance)
        final_events = {}
        current_pos = self.key
        for part in parts:
            if left.length <= part:
                self.voice.events[current_pos] = left
                current_pos = Position(
                    current_pos.position + left.length.length
                )
                break
            left, right = left.split(Length.from_fraction(part), tie=True)
            if right.length.length == 0:
                break
            final_events[current_pos] = left
            current_pos = Position(current_pos.position + left.length.length)
            left = right
        if self.key.bar_end_distance < event.length:
            final_events[current_pos] = append_part
        for pos, event in final_events.items():
            if event.length == 0:
                continue
            self.voice[pos].append(event)


class Voice:

    def __init__(self, voice_nr: int = 1) -> None:
        self.voice_nr = voice_nr
        self.events: Dict[Position, Event] = {}
        self.globals: Dict[Position, List[NotationEvent]] = {}

    @property
    def voice_str(self) -> str:
        repl = {1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five'}
        return f'voice{repl[self.voice_nr]}'

    def __getitem__(self, key: Position) -> EventPackager:
        return EventPackager(self, key)

    def __setitem__(self, key: Position, value: Event) -> None:
        self.events[key] = value

    def __contains__(self, key: Position) -> bool:
        return key in self.events

    def __repr__(self) -> str:
        return f"<Voice {self.voice_nr}: \n   {pformat(self.events,3)}>"

    def append_to_chord(self, position: Position, event: Event) -> None:
        # print(f'append_to_chord: {position}, {event}')
        if event.pitch.midi_pitch is None:
            return
        chord = self.events[position]
        if not isinstance(chord, Chord):
            chord = chord.make_chord()
            self.events[position] = chord
        if chord.length == event.length:
            chord.append(event)
            return
        elif chord.length < event.length:
            left, right = event.split(chord.length, tie=True)
            chord.append(left)
        else:  # chord.length > event.length
            left, right = chord.split(event.length, tie=True)
            left.append(event)
            self.events[position] = left
        if right.length == 0:
            return
        key = Position(position.position + left.length.length)
        self[key].append(right)

    def sort(self) -> 'Voice':
        """Sort events by their position, fixing overlaps."""
        positions = sorted(self.events.keys())
        for idx, pos in enumerate(positions):
            ev = self.events[pos]
            try:
                r_pos = positions[idx + 1]
            except IndexError:
                break
            if pos + ev.length > r_pos:
                left, right = ev.split(
                    Length(float(r_pos - pos) * 4), tie=True
                )
                if right.length.length == 0:
                    break
                self.events[pos] = left
                self[r_pos].append(right)
                return self.sort()
        return self

    def with_rests(self) -> 'Voice':
        out = Voice(self.voice_nr)
        last = Position(0)
        for position, event in sorted(self.events.items()):
            if position < last:
                _last_pos = list(out.events)[-1]
                raise ValueError(
                    "overlapping events found: {}, {}".format(
                        (_last_pos, out.events[_last_pos]), (position, event)
                    )
                )
            if distance := position.percize_distance(last):
                left, bars, right = distance
                if left:
                    out[last].append(
                        Event(left, Pitch(), voice_nr=self.voice_nr)
                    )
                for bar_nr in range(bars):
                    bar = last.bar + bar_nr
                    bar_info = rpr.Project().measure_info(bar)
                    bar_pos = Position(bar_info['start'])
                    bar_length = Length(
                        bar_info['end'] - bar_info['start'], full_bar=True
                    )
                    out[bar_pos].append(
                        Event(bar_length, Pitch(), voice_nr=self.voice_nr)
                    )
                if right:
                    out[Position(position.position - right.length)].append(
                        Event(right, Pitch(), voice_nr=self.voice_nr)
                    )
            out[position].append(event)
            last = Position(position.position + event.length.length)
        return out

    def with_tuplets(self) -> 'Voice':
        new_events = {}
        tuplet = None
        tuplet_opened = False
        for position, event in self.events.items():
            p_denom = position.fraction.denominator
            l_denom = event.length.fraction.denominator
            tuplet_length = l_denom != Fractured.closest_power_of_two(l_denom)
            tuplet_pos = p_denom != Fractured.closest_power_of_two(p_denom)
            for item in event.prefix:
                if isinstance(item, NotationTupletBegin):
                    tuplet_opened = True
            # print(tuplet_pos, tuplet_length, tuplet_opened)
            if (tuplet_pos or tuplet_length or tuplet_opened):
                # print(f"p_denom={p_denom}, l_denom={l_denom}")
                # print(f"appending {event} to tuplet")
                if tuplet is None:
                    tuplet = Tuplet(Length(0))
                    new_events[position] = tuplet
                tuplet.append(event)
                for item in event.postfix:
                    if isinstance(item, NotationTupletEnd):
                        tuplet_opened = False
                        tuplet = None
                continue
            if tuplet is not None and not tuplet_length and not tuplet_pos:
                # print(f"tuplet {tuplet} is complete")
                tuplet = None
            # print(f"appending {event} to dict")
            new_events[position] = event

        self.events = new_events
        return self

    def apply_global_events(
        self,
        global_events: Dict[Position, List[NotationEvent]],
        forced: bool = False
    ) -> 'Voice':
        for position, events in global_events.items():
            if position in self.events:
                for event in events:
                    event.apply_to_event(self.events[position])
            else:
                if position > max(self.events):
                    continue
                if not forced:
                    self.globals[position] = events
                else:
                    self.events[position] = GlobalNotationEvent(events)
        if forced:
            self.events = {k: self.events[k] for k in sorted(self.events)}
        return self

    def with_compressed_rests(self) -> 'Voice':
        last_event: Optional[Event] = None
        new = {}
        for position, event in self.events.items():
            if event.length.full_bar:
                if last_event is None:
                    last_event = event
                elif last_event.length == event.length:
                    if not last_event.length.bar_multiplier:
                        last_event.length.bar_multiplier += 1
                    last_event.length.bar_multiplier += 1
                    continue
                else:
                    last_event = event
            else:
                last_event = None
            new[position] = event
        self.events = new
        return self

    def finalized(self) -> 'Voice':
        self.sort()
        with_rests = self.with_rests()
        with_tuples = with_rests.with_tuplets()
        with_globals = with_tuples.apply_global_events(
            self.globals, forced=True
        )
        compressed_rests = with_globals.with_compressed_rests()
        return compressed_rests


class Staff:

    def __init__(
        self,
        staff_nr: int,
        clef: Optional[Clef] = None,
        parallel: bool = True
    ) -> None:
        self.staff_nr = staff_nr
        self.voices: List[Voice] = []
        if clef is None:
            if staff_nr > 1:
                clef = Clef.bass
            else:
                clef = Clef.treble
        self.clef = clef
        self.parallel = parallel

    def __repr__(self) -> str:
        return "<Staff {nr}, clef: {clef}, {voices}>".format(
            nr=self.staff_nr, clef=self.clef.ly_render(), voices=self.voices
        )

    def append(self, voice: Voice) -> None:
        self.voices.append(voice)

    def extend(self, voices: Iterable[Voice]) -> None:
        self.voices.extend(voices)

    def apply_global_events(
        self, global_events: Dict[Position, List[NotationEvent]]
    ) -> None:
        self.voices[0].apply_global_events(global_events)
        for voice in self.voices:
            voice.apply_global_events(global_events)

    def __getitem__(self, index: int) -> Voice:
        return self.voices[index]

    def __setitem__(self, index: int, voice: Voice) -> None:
        self.voices[index] = voice

    def __delitem__(self, index: int) -> None:
        del self.voices[index]

    def __iter__(self) -> Iterator[Voice]:
        for voice in self.voices:
            yield voice

    def __len__(self) -> int:
        return len(self.voices)


def get_time_signature_betveen_bounds(
    begin_s: float, end_s: float
) -> Dict[Position, List[NotationTimeSignature]]:
    times = {}
    pr = rpr.Project()
    i = 0
    num = 0
    denom = 0
    while True:
        i += 1
        info = pr.measure_info(i)
        # print(info)
        if info['start'] < begin_s and info['start'] != 0:
            continue
        if info['start'] > end_s or info['end'] >= end_s:
            break
        if (num, denom) != (info['num'], info['denom']):
            num, denom = info['num'], info['denom']
            times[Position(info['start'])] = [
                NotationTimeSignature(TimeSignature(num, denom))
            ]
    return times


def update_events(
    events: Dict[Position, List[EventT]],
    update: Dict[Position, List[EventT]],
    sort: bool = False
) -> Dict[Position, List[EventT]]:
    events = events.copy()
    for pos, event in update.items():
        if pos in events:
            events[pos].extend(event)
        else:
            events[pos] = event
    if sort:
        return {k: events[k] for k in sorted(events)}
    return events


def get_global_events(
    at_start: List[NotationEvent], begin_s: float, end_s: float
) -> Dict[Position, List[NotationEvent]]:
    # print('get global events')
    events: Dict[Position, List[NotationEvent]] = {}
    events[Position(0)] = at_start
    events = update_events(
        events, get_time_signature_betveen_bounds(begin_s, end_s)
    )
    pr = rpr.Project()
    for marker in pr.markers:
        # print(f'resolving marker {marker.name}')
        if NotationMarker.reascore_tokens(marker.name):
            pos = Position(pr.time_to_beats(marker.position))
            if pos not in events:
                events[pos] = []
            events[pos].extend(NotationMarker.from_reaper_marker(marker.name))
    return {k: events[k] for k in sorted(events)}


def notes_from_take(
    take: rpr.Take, pitch_type: TrackPitchType, note_names: List[str]
) -> Dict[Position, List[Event]]:
    events: Dict[Position, List[Event]] = {}
    for note in take.notes:
        info = note.infos
        if info['muted']:
            continue
        if pitch_type == TrackPitchType.note_names:
            if not note_names[info['pitch']]:
                continue
            pitch = Pitch(info['pitch'], note_name=note_names[info['pitch']])
        else:
            pitch = Pitch(info['pitch'])
        start = take.ppq_to_beat(info['ppq_position'])
        end = take.ppq_to_beat(info['ppq_end'])
        pos = Position(start)
        if pos not in events:
            events[pos] = []
        events[pos].append(Event(Length(end - start), pitch))
    return events


def _filter_notations(event: MIDIEventDict) -> bool:
    return NotationPitch.is_reascore_event(event)


def pitch_notations_from_take(
    take: rpr.Take
) -> Dict[Position, List[NotationPitch]]:
    events: Dict[Position, List[NotationPitch]] = {}

    for event in filter(_filter_notations, take.get_midi()):
        pos = Position(take.ppq_to_beat(event['ppq']))
        n_events = NotationPitch.from_midibuf(event['buf'])
        if pos not in events:
            events[pos] = []
        events[pos].extend(n_events)
    return events


def _filter_text(event: MIDIEventDict) -> bool:
    return NotationText.is_text_event(event)


def staff_notations_from_take(
    take: rpr.Take
) -> Dict[Position, List[NotationEvent]]:
    events: Dict[Position, List[NotationEvent]] = {}

    for event in filter(_filter_text, take.get_midi()):
        pos = Position(take.ppq_to_beat(event['ppq']))
        n_event = NotationText.from_midibuf(event['buf'])
        if pos not in events:
            events[pos] = []
        events[pos].append(n_event)
    return events


def filer_ignored_notes(
    events: Dict[Position, List[Event]]
) -> Dict[Position, List[Event]]:
    new = {}
    for pos, evts in events.items():
        new_events = []
        for event in evts:
            if NotationIgnore(event.pitch) not in event.prefix:
                new_events.append(event)
        new[pos] = new_events
    return new


@rpr.inside_reaper()
def events_from_take(
    take: rpr.Take, pitch_type: TrackPitchType, note_names: List[str]
) -> Dict[Position, List[Event]]:
    # events: Dict[Position, List[Event]] = {}
    note_events = notes_from_take(take, pitch_type, note_names)
    pitch_notations = pitch_notations_from_take(take)
    staff_notations = staff_notations_from_take(take)
    for pos, notes in note_events.items():
        for note in notes:
            if pos in pitch_notations:
                for notation in pitch_notations[pos]:
                    if notation.pitch.midi_pitch == note.pitch.midi_pitch:
                        notation.apply_to_event(note)
    for pos, n_events in staff_notations.items():
        if pos not in note_events:
            note_events[pos] = [Event(Length.from_fraction(1 / 16), Pitch())]
        for n_event in n_events:
            n_event.apply_to_event(note_events[pos][0])
    note_events = filer_ignored_notes(note_events)
    return note_events


def split_by_voice(events: Dict[Position, List[Event]]) -> Dict[int, Voice]:
    voices: Dict[int, Voice] = {}
    for position, event_list in events.items():
        for event in event_list:
            key = event.voice_nr
            if key not in voices:
                voices[key] = Voice(key)
            voice = voices[key]
            voice[position].append(event)
    temp = voices
    voices = {}
    for nr in sorted(temp):
        voices[nr] = temp[nr]
    for voice in voices.values():
        voice.sort()
    # pprint(voices)
    return voices


def split_by_staff(events: Dict[Position, List[Event]]) -> List[Staff]:
    staff_dicts: Dict[int, Dict[Position, List[Event]]] = {}
    for position, event_list in events.items():
        for event in event_list:
            key = event.staff_nr
            if key not in staff_dicts:
                staff_dicts[key] = {}
            staff = staff_dicts[key]
            if position not in staff:
                staff[position] = []
            staff[position].append(event)
    staffs: List[Staff] = []
    for nr in sorted(staff_dicts):
        events = staff_dicts[nr]
        staffs.append(Staff(nr))
        voices = split_by_voice(events)
        staffs[-1].extend(voices.values())
    return staffs


class BarCheck(Attachment):

    def __init__(self, bar_nr: Optional[int] = None) -> None:
        self.bar_nr = bar_nr

    def ly_render(self) -> str:
        barchek = ' | '
        if self.bar_nr:
            return f'{barchek}\n\n% bar # {self.bar_nr}\n'
        return barchek

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BarCheck) and other.bar_nr == self.bar_nr:
            return True
        return False

    def __repr__(self) -> str:
        return f'<BarCheck at bar {self.bar_nr}>'


if __name__ == '__main__':
    events = events_from_take(rpr.Project().selected_items[0].active_take)
    pprint(events)
    print('\n-------------------\n')
    voice = split_by_voice(events)[1]
    pprint(voice)
    print('\n-------------------\n')
    voice = voice.with_rests()
    pprint(voice)
    print('\n-------------------\n')
