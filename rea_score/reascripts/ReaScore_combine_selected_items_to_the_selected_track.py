from typing import Callable, List
from rea_score.primitives import NotationPitch
import reapy as rpr


class NormalizedMIDI(rpr.MIDIEventDict):
    pos_sec: float


def get_midi_with_global_position(
    take: rpr.Take, filter_f: Callable[[rpr.MIDIEventDict], bool]
) -> List[NormalizedMIDI]:
    midi = filter(filter_f, take.get_midi())
    new: List[NormalizedMIDI] = []
    for event in midi:
        new.append(
            NormalizedMIDI(
                buf=event['buf'],
                cc_shape=event['cc_shape'],
                muted=event['muted'],
                ppq=event['ppq'],
                selected=event['selected'],
                pos_sec=take.ppq_to_time(event['ppq'])
            )
        )
    return new


def combine_midi(*midi_lists: List[NormalizedMIDI]) -> List[NormalizedMIDI]:
    out = []
    for midi_list in midi_lists:
        out.extend(midi_list)
    return sorted(out, key=lambda d: d['pos_sec'])


def make_item_on_target_track(track: rpr.Track) -> rpr.Item:
    start, end = track.project.length, .0
    for item in track.project.selected_items:
        i_start = item.position
        i_end = i_start + item.length
        if i_start < start:
            start = i_start
        if i_end > end:
            end = i_end
    return track.add_midi_item(start, end)


def midi_to_item(midi: List[NormalizedMIDI], item: rpr.Item) -> None:
    new_midi: List[rpr.MIDIEventDict] = []
    take = item.active_take
    for event in midi:
        new_midi.append(
            rpr.MIDIEventDict(
                ppq=take.time_to_ppq(event['pos_sec']),
                buf=event['buf'],
                selected=event['selected'],
                muted=event['muted'],
                cc_shape=event['cc_shape'],
            )
        )

    take.set_midi(new_midi, sort=True)


def filter_midi(event: rpr.MIDIEventDict) -> bool:
    if event['muted']:
        return False
    if 0x80 <= event['buf'][0] < 0xb0:
        return True
    if NotationPitch.is_reascore_event(event):
        return True
    return False


@rpr.inside_reaper()
def combine() -> None:
    pr = rpr.Project()
    track = pr.selected_tracks[0]
    midi_lists = []
    for item in pr.selected_items:
        midi_lists.append(
            get_midi_with_global_position(item.active_take, filter_midi)
        )
    item = make_item_on_target_track(track)
    midi_to_item(combine_midi(*midi_lists), item)


combine()
