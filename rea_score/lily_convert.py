from fractions import Fraction
from warnings import warn
from typing import Dict, List, NewType, Optional, Tuple, TypedDict, Union
import re

from rea_score.dom import EventT, TrackType
from rea_score.notation_events import NotationKeySignature

from .dom import Staff, StaffGroup, Voice, events_from_take, split_by_voice
from .primitives import (
    ALPHABET, PITCH_IS_SPACER, Chord, Event, GlobalNotationEvent, Grace, Key, Length, Pitch,
    Position, Scale, Tuplet, Clef
)

# import reapy_boost as rpr
# import abjad

KEY = Key('c', Scale.major)


class LyDict(TypedDict):
    var: str
    definition: str
    expression: str


def render_score(parts: List[LyDict]) -> str:
    ...


def normalize_name(name: str) -> str:
    name = re.sub(r'\s', '_', name)
    if m := re.search(r'(\d+)', name):
        name = re.sub(r'\d+', ALPHABET[int(m.group(0))], name)
    return name


_part_definition = """{staff_defs}\n{var} = << {staff_expressions} >>"""
_part_expression = """\\new {staffGroup} \\{var}"""


def render_part(
    name: str,
    staves: List[Staff],
    track_type: TrackType,
    octave_offset: int,
    staff_group: StaffGroup = StaffGroup.GrandStaff,
) -> LyDict:
    name_var = normalize_name(name)
    if len(staves) > 0:
        name_var = ''
    rendered = [
        render_staff(staff, track_type, octave_offset, name=name_var)
        for staff in staves
    ]
    if len(rendered) == 1:
        return rendered[0]
    return LyDict(
        var=name,
        definition=_part_definition.format(
            staff_defs='\n'.join(
                list([staff['definition'] for staff in rendered])
            ),
            var=name,
            staff_expressions=' '.join(
                list([staff['expression'] for staff in rendered])
            )
        ),
        expression=_part_expression.format(
            staffGroup=staff_group.value, var=name
        )
    )


_staff_definition = """{voice_defs}\n{var} = <<{clef} {voice_vars} >>"""
_staff_expression = """\\new {staff_str} = "{staff_name}" {staff_params} {{\\{var}}}"""
_staff_params = """\\with {{{staff_params}}}"""


def render_staff(
    staff: Staff,
    track_type: TrackType,
    octave_offset: int,
    name: str = ''
) -> LyDict:
    staff_str = 'Staff'
    if track_type == TrackType.drums:
        staff_str = 'DrumStaff'
        staff.clef = Clef.percussion
    elif track_type == TrackType.one_line_perc:
        staff.clef = Clef.percussion
        staff_str = (
            'DrumStaff \\with{\n'
            'drumStyleTable = #percussion-style\n'
            '\\override StaffSymbol.line-count = #1}'
        )
    elif track_type == TrackType.bongos:
        staff.clef = Clef.percussion
        staff_str = (
            'DrumStaff \\with{\n'
            'drumStyleTable = #bongos-style\n'
            '\\override StaffSymbol.line-count = #2}'
        )

    litera = ALPHABET[staff.staff_nr]
    if name:
        var = name
    else:
        var = f'Staff{litera}'

    staff_params = []
    voice_defs = []
    voice_expressions = []
    if len(staff) == 2:
        combine = '\\partCombine '
        staff_params.append('printPartCombineTexts = ##f')
    else:
        combine = ''
    for voice in staff:
        voice_dict = render_voice(
            voice,
            voice.voice_nr,
            track_type=track_type,
            octave_offset=octave_offset,
            name=var + "Voice" + ALPHABET[voice.voice_nr]
        )
        voice_defs.append(voice_dict['definition'])
        voice_expressions.append(voice_dict['expression'])
    return LyDict(
        var=var,
        definition=_staff_definition.format(
            voice_defs='\n'.join(voice_defs),
            var=var,
            clef=staff.clef.ly_render(),
            voice_vars=combine + " ".join(voice_expressions),
        ),
        expression=_staff_expression.format(
            staff_str=staff_str,
            staff_name=var,
            var=var,
            staff_params=_staff_params.format(
                staff_params='\n'.join(staff_params)
            )
        )
    )


_voice_definition = """\
{var} =  {mode} {{
    {voice_str} {events}
}}
"""
_voice_expression = """\\{var}"""


def render_voice(
    voice: Voice,
    index: int = 1,
    track_type: TrackType = TrackType.default,
    octave_offset: int = 0,
    name=''
) -> LyDict:
    # print(f"finalizing voice {voice}")
    key = KEY
    voice = voice.finalized()
    print(voice.globals)
    voice_str = ''
    if index != 1:
        voice_str = voice.voice_str
    voicedef = 'Voice'

    mode = ''
    if track_type in (
        TrackType.drums, TrackType.one_line_perc, TrackType.bongos
    ):
        # voice_str = 'stemUp' if index == 1 else 'stemDown'
        if index != 1:
            voice_str = 'stemDown'
        voicedef = 'DrumVoice'
        mode = '\\drummode'

    litera = ALPHABET[index]
    var = f'\\Voice{litera}'
    if name:
        var = name

    out = []
    for event in voice.events.values():
        event_str = ''
        event_str, key = render_any_event(event, key, octave_offset)
        out.append(event_str)
    # key = KEY.ly_render()
    if voice_str:
        voice_str = '\\' + voice_str
    return LyDict(
        definition=_voice_definition.format(
            var=var,
            mode=mode,
            voice_str=voice_str,
            # voice_str="",
            events=' '.join(out),
        ),
        expression=_voice_expression.format(
            voice_def=voicedef,
            litera=litera,
            var=var,
        ),
        var=var,
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
        prefix=render_prefix(event, key, octave_offset),
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
        prefix=render_prefix(chord, key, octave_offset),
        pitches=' '.join(pitches),
        length=length,
        postfix=render_postfix(chord),
        tie=tie,
        tied=tied
    )


def render_tuplet(tuplet: Tuplet, key: Key,
                  octave_offset: int) -> Tuple[str, Key]:
    string = "{prefix}\\tuplet {rate} {{{events}}}"
    events_str = []
    for event in tuplet.events:
        event_str, key = render_any_event(event, key, octave_offset)
        events_str.append(event_str)
    return string.format(
        prefix=render_prefix(tuplet, key, octave_offset),
        rate=tuplet.rate.to_str(),
        events=' '.join(ev for ev in events_str)
    ), key


def render_grace(grace: Grace, key: Key, octave_offset: int) -> str:
    string = "{prefix} {events} {postfix}"
    events_str = []
    for event in grace.events:
        event_str, key = render_any_event(event, key, octave_offset)
        events_str.append(event_str)
    return string.format(
        prefix=render_prefix(grace, key, octave_offset),
        grace_type=grace.grace_type.value,
        events=' '.join(ev for ev in events_str),
        postfix=render_postfix(grace)
    )


def render_prefix(event: Event, key: Key, octave_offset: int) -> str:
    elms = []
    for elm in event.prefix:
        if isinstance(elm, Grace):
            # print(elm)
            elms.append(render_grace(elm, key, octave_offset))
        else:
            elms.append(elm.ly_render())
    string = ' '.join(elm for elm in elms)
    if string:
        return string + ' '
    else:
        return ''


def render_postfix(event: Event) -> str:
    string = ' '.join(elm.ly_render() for elm in event.postfix)
    if string:
        return string + ' '
    else:
        return ''


def render_length(length: Length, rest: bool = False) -> Tuple[str, str]:
    tied = ''
    tie = '~ '
    trem = '' if not length.trem_denom else f':{length.trem_denom}'
    bar = '' if not length.bar_multiplier else f'*{length.bar_multiplier}'
    if rest:
        tie = ' r'
        if length.full_bar:
            tie = ' R'
    for idx, lth in enumerate(reversed(length.normalized(length.fraction))):
        if idx == 0:
            # COMMENTED BECAUSE BAR CAN BE LONGER THEN 1, WAIT FOR BUGS
            # if lth > 1:
            #     f_lth = '1'
            #     tied += tie + fraction_to_length(lth - 1) + trem + bar
            # else:
            #     f_lth = fraction_to_length(lth) + trem + bar
            f_lth = fraction_to_length(lth) + trem + bar
        else:
            tied += tie + fraction_to_length(lth) + trem + bar
        # print(idx, lth, f_lth, tied, sep=', ')
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
    # print(frac, denom, num)
    return denom + num


def render_pitch(pitch: Pitch, key: Key,
                 octave_offset: int) -> Tuple[str, str]:
    if pitch.midi_pitch not in (None, PITCH_IS_SPACER):
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
