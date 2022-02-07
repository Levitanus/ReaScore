from fractions import Fraction
from warnings import warn
from typing import Dict, List, NewType, Optional, Tuple, Union
import re

from rea_score.dom import EventT, TrackType
from rea_score.primitives import NotationKeySignature

from .dom import Staff, Voice, events_from_take, split_by_voice
from .primitives import (
    Chord, Event, GlobalNotationEvent, Key, Length, Pitch, Position, Scale,
    Tuplet, Clef
)

# import reapy as rpr
# import abjad

KEY = Key('c', Scale.major)


def render_part(
    staves: List[Staff], track_type: TrackType, octave_offset: int
) -> str:
    if len(staves) == 1:
        return render_staff(staves[0], track_type, octave_offset)
    group = 'GrandStaff'
    part_string = """\\new {group} <<{staves}>>"""
    return part_string.format(
        group=group,
        staves='\n'.join(
            render_staff(staff, track_type, octave_offset) for staff in staves
        )
    )


def render_staff(
    staff: Staff, track_type: TrackType, octave_offset: int
) -> str:
    staff_string = """\\new {staff_str} <<{clef} {voices}>>"""
    staff_str = 'Staff'
    if track_type == TrackType.drums:
        staff_str = 'DrumStaff'
        staff.clef = Clef.percussion
    elif track_type == TrackType.one_line_perc:
        staff.clef = Clef.percussion
        staff_str = """\
        DrumStaff \\with{
        drumStyleTable = #percussion-style
        \\override StaffSymbol.line-count = #1}
        """
    elif track_type == TrackType.bongos:
        staff.clef = Clef.percussion
        staff_str = """\
        DrumStaff \\with{
        drumStyleTable = #bongos-style
        \\override StaffSymbol.line-count = #2}
        """
    rendered_voices = []
    for voice in staff:
        rendered_voices.append(
            render_voice(
                voice,
                voice.voice_nr,
                track_type=track_type,
                octave_offset=octave_offset
            )
        )
    return staff_string.format(
        staff_str=staff_str,
        clef=staff.clef.ly_render(),
        voices='\n'.join(rendered_voices)
    )


def render_voice(
    voice: Voice,
    index: Optional[int] = None,
    name: Optional[str] = None,
    track_type: TrackType = TrackType.default,
    octave_offset: int = 0,
) -> str:
    # print(f"finalizing voice {voice}")
    key = KEY
    voice = voice.finalized()
    args = {}
    voice_str = voice.voice_str
    voicedef = 'Voice'
    mode = ''
    if track_type in (
        TrackType.drums, TrackType.one_line_perc, TrackType.bongos
    ):
        voice_str = 'stemUp' if index == 1 else 'stemDown'
        voicedef = 'DrumVoice'
        mode = '\\drummode'
    if name:
        if index:
            name = f'{name}index'
        args['name'] = name
    out = []
    for event in voice.events.values():
        event_str = ''
        event_str, key = render_any_event(event, key, octave_offset)
        out.append(event_str)
    # key = KEY.ly_render()
    return "\\new {voicedef} = \"{idx}\" {mode} {{\\{voicestr} {voiceout}}}".format(
        voicedef=voicedef,
        idx=index,
        mode=mode,
        voicestr=voice_str,
        voiceout=' '.join(out)
    )


def render_any_event(
    event: Union[Event, GlobalNotationEvent], key: Key, octave_offset: int
) -> Tuple[str, Key]:
    if isinstance(event, Event):
        for attach in event.prefix:
            if isinstance(attach, NotationKeySignature):
                key = attach.key
    # print(event, key)
    if isinstance(event, Chord):
        event_str = render_chord(event, key, octave_offset)
    elif isinstance(event, Tuplet):
        event_str, key = render_tuplet(event, key, octave_offset)
    elif isinstance(event, Event):
        event_str = render_event(event, key, octave_offset)
    elif isinstance(event, GlobalNotationEvent):
        for ev in event.events:
            if isinstance(ev, NotationKeySignature):
                key = ev.key
        event_str = event.ly_render()
    else:
        raise TypeError(event)
    return event_str, key


def render_event(event: Event, key: Key, octave_offset: int) -> str:
    string = "{prefix}{pitch}{length}{postfix}{tie}{tied}"
    if event.length == 0:
        warn(f'Zero-kength event: {event}, returning null')
        return ''
    length, tied = render_length(
        event.length, rest=(event.pitch.midi_pitch is None)
    )
    pitch, tie = render_pitch(event.pitch, key, octave_offset)
    if event.length.full_bar:
        pitch = re.sub('r', 'R', pitch)
    # if tied and tie:
    #     tie = ''
    return string.format(
        prefix=render_prefix(event),
        pitch=pitch,
        length=length,
        postfix=render_postfix(event),
        tie=tie,
        tied=tied
    )


def render_chord(chord: Chord, key: Key, octave_offset: int) -> str:
    string = "{prefix}<{pitches}>{length}{postfix}{tie}{tied}"
    pitches = []
    for pitch in chord.pitches:
        pitches.append(''.join(render_pitch(pitch, key, octave_offset)))
    length, tied = render_length(chord.length)
    if tied:
        tie = '~'
    else:
        tie = ''
    return string.format(
        prefix=render_prefix(chord),
        pitches=' '.join(pitches),
        length=length,
        postfix=render_postfix(chord),
        tie=tie,
        tied=tied
    )


def render_tuplet(tuplet: Tuplet, key: Key,
                  octave_offset: int) -> Tuple[str, Key]:
    string = "{prefix} \\tuplet {rate} {{{events}}}"
    events_str = []
    for event in tuplet.events:
        event_str, key = render_any_event(event, key, octave_offset)
        events_str.append(event_str)
    return string.format(
        prefix=render_prefix(tuplet),
        rate=tuplet.rate.to_str(),
        events=' '.join(ev for ev in events_str)
    ), key


def render_prefix(event: Event) -> str:
    return ' '.join(elm.ly_render() for elm in event.prefix) + ' '


def render_postfix(event: Event) -> str:
    return ' '.join(elm.ly_render() for elm in event.postfix) + ' '


def render_length(length: Length, rest: bool = False) -> Tuple[str, str]:
    tied = ''
    tie = '~ '
    trem = '' if not length.trem_denom else f':{length.trem_denom}'
    if rest:
        tie = ' r'
    for idx, lth in enumerate(reversed(length.normalized(length.fraction))):
        if idx == 0:
            if lth > 1:
                f_lth = '1'
                tied += fraction_to_length(lth - 1) + trem
            else:
                f_lth = fraction_to_length(lth) + trem
        else:
            tied += tie + fraction_to_length(lth) + trem
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


def render_pitch(pitch: Pitch, key: Key,
                 octave_offset: int) -> Tuple[str, str]:
    if pitch.midi_pitch is not None:
        pitch.midi_pitch += octave_offset * 12
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
