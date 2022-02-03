from fractions import Fraction
from warnings import warn
from typing import Dict, List, NewType, Optional, Tuple, Union
import re

from rea_score.dom import EventT
from rea_score.primitives import NotationKeySignature

from .dom import Staff, Voice, events_from_take, split_by_voice
from .primitives import Chord, Event, GlobalNotationEvent, Key, Length, Pitch, Position, Scale, Tuplet

# import reapy as rpr
# import abjad

KEY = Key('c', Scale.major)


def render_part(staves: List[Staff]) -> str:
    if len(staves) == 1:
        return render_staff(staves[0])
    group = 'GrandStaff'
    part_string = """\\new {group} <<{staves}>>"""
    return part_string.format(
        group=group, staves='\n'.join(render_staff(staff) for staff in staves)
    )


def render_staff(staff: Staff) -> str:
    staff_string = """\\new Staff <<{clef} {voices}>>"""
    rendered_voices = []
    for voice in staff:
        rendered_voices.append(render_voice(voice, voice.voice_nr))
    return staff_string.format(
        clef=staff.clef.ly_render(), voices='\n'.join(rendered_voices)
    )


def render_voice(
    voice: Voice,
    index: Optional[int] = None,
    name: Optional[str] = None
) -> str:
    # print(f"finalizing voice {voice}")
    key = KEY
    voice = voice.finalized()
    args = {}
    if name:
        if index:
            name = f'{name}index'
        args['name'] = name
    out = []
    for event in voice.events.values():
        event_str = ''
        event_str, key = render_any_event(event, key)
        out.append(event_str)
    # key = KEY.ly_render()
    return f"\\new Voice = \"{voice.voice_nr}\" {{\\{voice.voice_str} {' '.join(out)}}}"


def render_any_event(event: Union[Event, GlobalNotationEvent],
                     key: Key) -> Tuple[str, Key]:
    if isinstance(event, Event):
        for attach in event.prefix:
            if isinstance(attach, NotationKeySignature):
                key = attach.key
    print(event, key)
    if isinstance(event, Chord):
        event_str = render_chord(event, key)
    elif isinstance(event, Tuplet):
        event_str, key = render_tuplet(event, key)
    elif isinstance(event, Event):
        event_str = render_event(event, key)
    elif isinstance(event, GlobalNotationEvent):
        for ev in event.events:
            if isinstance(ev, NotationKeySignature):
                key = ev.key
        event_str = event.ly_render()
    else:
        raise TypeError(event)
    return event_str, key


def render_event(event: Event, key: Key) -> str:
    string = "{preambula}{pitch}{length}{notations}{tie}{tied}"
    if event.length == 0:
        warn(f'Zero-kength event: {event}, returning null')
        return ''
    length, tied = render_length(
        event.length, rest=(event.pitch.midi_pitch is None)
    )
    pitch, tie = render_pitch(event.pitch, key)
    if event.length.full_bar:
        pitch = re.sub('r', 'R', pitch)
    # if tied and tie:
    #     tie = ''
    return string.format(
        preambula=render_prefix(event),
        pitch=pitch,
        length=length,
        notations='',
        tie=tie,
        tied=tied
    )


def render_chord(chord: Chord, key: Key) -> str:
    string = "{preambula}<{pitches}>{length}{notations}{tie}{tied}"
    pitches = []
    for pitch in chord.pitches:
        pitches.append(''.join(render_pitch(pitch, key)))
    length, tied = render_length(chord.length)
    if tied:
        tie = '~'
    else:
        tie = ''
    return string.format(
        preambula=render_prefix(chord),
        pitches=' '.join(pitches),
        length=length,
        notations='',
        tie=tie,
        tied=tied
    )


def render_tuplet(tuplet: Tuplet, key: Key) -> Tuple[str, Key]:
    string = "{prefix} \\tuplet {rate} {{{events}}}"
    events_str = []
    for event in tuplet.events:
        event_str, key = render_any_event(event, key)
        events_str.append(event_str)
    return string.format(
        prefix=render_prefix(tuplet),
        rate=tuplet.rate.to_str(),
        events=' '.join(ev for ev in events_str)
    ), key


def render_prefix(event: Event) -> str:
    return ' '.join(elm.ly_render() for elm in event.prefix) + ' '


def render_length(length: Length, rest: bool = False) -> Tuple[str, str]:
    tied = ''
    tie = '~ '
    if rest:
        tie = ' r'
    for idx, lth in enumerate(reversed(length.normalized(length.fraction))):
        if idx == 0:
            if lth > 1:
                f_lth = '1'
                tied += fraction_to_length(lth - 1)
            else:
                f_lth = fraction_to_length(lth)
        else:
            tied += tie + fraction_to_length(lth)
    return f_lth, tied


class FracError(ValueError):
    ...


def fraction_to_length(frac: Fraction) -> str:
    num = ''
    if frac.numerator == 3:
        num = '.'
        frac = frac / 3 * 2
        denom = str(frac.denominator)
    elif frac.denominator == 1 and frac.numerator > 1:
        denom = '~'.join(['1'] * frac.numerator)
    elif frac.numerator == 1:
        denom = str(frac.denominator)
    else:
        raise FracError(f"no right condition {frac}")
    # print(frac)
    return denom + num


def render_pitch(pitch: Pitch, key: Key) -> Tuple[str, str]:
    string = pitch.named_pitch(key)
    string = re.sub('♯', 'is', string)
    string = re.sub('♭', 'es', string)
    if m := re.match(r'(.+)(\d)', string):
        name, octave = m.groups()
        diff = int(octave) - 3
        if diff > 0:
            octave = "'" * diff
        elif diff < 0:
            octave = "," * -diff
        else:
            octave = ''
    else:
        name = pitch.named_pitch(key)
        octave = ''
    if pitch.tie:
        tie = '~'
    else:
        tie = ''
    return name.lower() + octave, tie
