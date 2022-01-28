from typing import Dict, List, Optional
import reapy as rpr

# from reapy import reascript_api as RPR

from .primitives import (
    Attachment, Chord, Event, Length, Pitch, Position, Fractured
)

from pprint import pformat, pprint


class EventPackager:

    def __init__(self, voice: 'Voice', key: Position) -> None:
        self.voice = voice
        self.key = key

    def append(self, event: Event) -> None:
        if self.key not in self.voice.events:
            if self.key.bar_position == 0:
                barcheck = BarCheck(self.key.bar)
                if self.key.position != 0 and barcheck not in event.preambula:
                    # print(f'add barcheck at {self.key} to the {event}')
                    event.preambula.append(barcheck)
            # if self.key.bar_end_distance < event.length:
            return self.split_by_position(event)
            self.voice.events[self.key] = event
            return
        self.voice.append_to_chord(self.key, event)
        # raise NotImplementedError()

    def split_by_position(self, event: Event) -> None:
        if self.key.bar_end_distance < event.length:
            left, append_part = event.split(
                Length(float(self.key.bar_end_distance) * 4), tie=True
            )
        else:
            left = event
        parts = Fractured.normalized(self.key.bar_end_distance)
        # print(
        #     'split:',
        #     left,
        #     # append_part,
        #     parts,
        #     sep='\n- ',
        # )
        final_events = {}
        current_pos = self.key
        for part in parts:
            print(left, part)
            if left.length <= part:
                self.voice.events[current_pos] = left
                current_pos = Position(
                    current_pos.position + left.length.length
                )
                break
            left, right = left.split(Length.from_fraction(part), tie=True)
            final_events[current_pos] = left
            current_pos = Position(current_pos.position + left.length.length)
            left = right
        if self.key.bar_end_distance < event.length:
            final_events[current_pos] = append_part
        # pprint(final_events)
        for pos, event in final_events.items():
            self.voice[pos].append(event)


class Voice:

    def __init__(self, voice_nr: int = 1) -> None:
        self.voice_nr = voice_nr
        self.events: Dict[Position, Event] = {}

    def __getitem__(self, key: Position) -> EventPackager:
        return EventPackager(self, key)

    def __setitem__(self, key: Position, value: Event) -> None:
        self.events[key] = value

    def __contains__(self, key: Position) -> bool:
        return key in self.events

    def __repr__(self) -> str:
        return f"<Voice {self.voice_nr}: \n   {pformat(self.events,3)}>"

    def append_to_chord(self, position: Position, event: Event) -> None:
        if event.pitch.midi_pitch is None:
            return
        chord = self.events[position]
        if not isinstance(chord, Chord):
            chord = chord.make_chord()
        # print('append_to_chord:', position, chord, event, sep='\n    ')
        if chord.length == event.length:
            # print('    leght are equal, append')
            chord.append(event)
            return
        elif chord.length < event.length:
            left, right = event.split(chord.length, tie=True)
            chord.append(left)
            # print('    chord is shorter:', chord, right, sep='\n' + ' ' * 8)
        else:  # chord.length > event.length
            left, right = chord.split(event.length, tie=True)
            left.append(event)
            self.events[position] = left
            # print('    chord is longer:', left, right, sep='\n' + ' ' * 8)
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
                self.events[pos] = left
                self[r_pos].append(right)
                return self.sort()
        return self

    def with_rests(self) -> 'Voice':
        out = Voice()
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
                print(f'left={left}, bars={bars}, right={right}')
                if left:
                    out[last].append(
                        Event(left, Pitch(), voice_nr=self.voice_nr)
                    )
                for bar_nr in range(bars):
                    bar = last.bar + bar_nr
                    print(bar, last.bar, bar_nr)
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


@rpr.inside_reaper()
def events_from_take(take: rpr.Take) -> Dict[Position, List[Event]]:
    events: Dict[Position, List[Event]] = {}
    for note in take.notes:
        info = note.infos
        start = take.ppq_to_beat(info['ppq_position'])
        end = take.ppq_to_beat(info['ppq_end'])
        # print(start, end)
        pos = Position(start)
        if pos not in events:
            events[pos] = []
        events[pos].append(Event(Length(end - start), Pitch(info['pitch'], )))
    return events


def split_by_voice(events: Dict[Position, List[Event]]) -> Dict[int, Voice]:
    voices: Dict[int, Voice] = {}
    for position, event_list in events.items():
        for event in event_list:
            key = event.voice_nr
            if key not in voices:
                voices[key] = Voice(key)
            voice = voices[key]
            voice[position].append(event)
    for voice in voices.values():
        voice.sort()
    return voices


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
