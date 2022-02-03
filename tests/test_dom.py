from rea_score.dom import BarCheck, EventPackager, Voice
from rea_score.primitives import Event, Length, Pitch, Position

from pprint import pprint


def test_event_packager():
    voice = Voice()
    length = Length(9)
    position = Position(1.5)
    event = Event(length, Pitch(60))
    assert position.bar_end_distance < event.length
    EventPackager(voice, position).append(event)
    # pprint(voice.events)
    voice.events = {k: voice.events[k] for k in sorted(voice.events)}
    expected_events = {
        Position.from_fraction(3 / 8):
            Event(Length.from_fraction(1 / 8), Pitch(60, tie=True)),
        Position.from_fraction(1 / 2):
            Event(Length.from_fraction(1 / 2), Pitch(60, tie=True)),
        Position.from_fraction(1):
            Event(
                Length.from_fraction(1),
                Pitch(60, tie=True),
                prefix=[BarCheck(2)]
            ),
        Position.from_fraction(2):
            Event(
                Length.from_fraction(5 / 8),
                Pitch(60, tie=False),
                prefix=[BarCheck(3)]
            ),
    }
    pprint(list(zip(voice.events.items(), expected_events.items())))
    assert voice.events == expected_events

    voice = Voice()
    voice[Position.from_fraction(3 / 8)].append(
        Event(Length.from_fraction(1 / 2), Pitch(60))
    )
    expected_events = {
        Position.from_fraction(3 / 8):
            Event(Length.from_fraction(1 / 8), Pitch(60, tie=True)),
        Position.from_fraction(1 / 2):
            Event(Length.from_fraction(3 / 8), Pitch(60)),
    }
    assert voice.events == expected_events
