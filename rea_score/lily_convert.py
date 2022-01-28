from fractions import Fraction
from warnings import warn
from typing import Dict, List, NewType, Optional, Tuple, Union
import re

from .dom import Voice, events_from_take, split_by_voice
from .primitives import Chord, Event, Key, Length, Pitch, Position, Scale

import reapy as rpr
import abjad

KEY = Key('fis', Scale.major)


def render_staff(voices: Dict[int, Voice]) -> str:
    staff = """\\new Staff <<{voices}>>"""
    rendered_voices = []
    for index, voice in voices.items():
        rendered_voices.append(render_voice(voice, index))
    return staff.format(voices='\n'.join(rendered_voices))


def render_voice(
    voice: Voice,
    index: Optional[int] = None,
    name: Optional[str] = None
) -> str:
    voice.sort()
    voice = voice.with_rests()
    args = {}
    if name:
        if index:
            name = f'{name}index'
        args['name'] = name
    out = []
    for event in voice.events.values():
        if isinstance(event, Chord):
            out.append(render_chord(event))
        elif isinstance(event, Event):
            out.append(render_event(event))
        else:
            raise TypeError(event)
    key = KEY.ly_render()
    return f"\\new Voice {{{key} {' '.join(out)}}}"


def render_event(event: Event) -> str:
    string = "{preambula}{pitch}{length}{notations}{tie}{tied}"
    if event.length == 0:
        warn(f'Zero-kength event: {event}, returning null')
        return ''
    length, tied = render_length(
        event.length, rest=(event.pitch.midi_pitch is None)
    )
    pitch, tie = render_pitch(event.pitch)
    if event.length.full_bar:
        pitch = re.sub('r', 'R', pitch)
    # if tied and tie:
    #     tie = ''
    return string.format(
        preambula=render_preambula(event),
        pitch=pitch,
        length=length,
        notations='',
        tie=tie,
        tied=tied
    )


def render_chord(chord: Chord) -> str:
    string = "{preambula}<{pitches}>{length}{notations}{tie}{tied}"
    pitches = []
    for pitch in chord.pitches:
        pitches.append(''.join(render_pitch(pitch)))
    length, tied = render_length(chord.length)
    if tied:
        tie = '~'
    else:
        tie = ''
    return string.format(
        preambula=render_preambula(chord),
        pitches=' '.join(pitches),
        length=length,
        notations='',
        tie=tie,
        tied=tied
    )


def render_preambula(event: Event) -> str:
    # out = ''
    # for elm in event.preambula:
    #     out += elm.ly_render()
    # return out
    return ''.join(elm.ly_render() for elm in event.preambula)


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


def render_pitch(pitch: Pitch) -> Tuple[str, str]:
    string = pitch.named_pitch(KEY)
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
        name = pitch.named_pitch(KEY)
        octave = ''
    if pitch.tie:
        tie = '~'
    else:
        tie = ''
    return name.lower() + octave, tie


def any_to_lily(obj: Union[Voice, rpr.Take]) -> str:
    if isinstance(obj, rpr.Take):
        return render_staff(split_by_voice(events_from_take(obj)))
    if isinstance(obj, Voice):
        return render_voice(obj)
    raise TypeError("Actually not literally any!")


if __name__ == '__main__':
    with rpr.inside_reaper():
        print(any_to_lily(rpr.Project().selected_items[0].active_take))
