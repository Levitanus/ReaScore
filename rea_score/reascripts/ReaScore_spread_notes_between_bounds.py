import typing as ty
import reapy_boost as rpr


def get_bounds(midi: ty.Iterable[rpr.MIDIEventDict]) -> ty.Tuple[float, float]:
    start, end = float('inf'), 0
    for event in midi:
        if not event['selected']:
            continue
        if start > event['ppq']:
            start = event['ppq']
        if end < event['ppq']:
            end = event['ppq']
    return start, end


def spread_times(notes: ty.List[rpr.Note], start: float,
                 end: float) -> ty.List[int]:
    step = (end - start) / (len(notes))
    times = []
    for i in range(len(notes) + 1):
        times.append(int(start + i * step))
    return times


@rpr.inside_reaper()
def spread() -> None:
    take = rpr.Project().selected_items[0].active_take
    midi = take.get_midi()
    # filtered = ty.cast(
    #     ty.Tuple[rpr.MIDIEventDict],
    #     tuple(
    #         filter(
    #             lambda event: event['selected'] and event['buf'][0] == 144,
    #             midi
    #         )
    #     )
    # )
    start_ppq, end_ppq = get_bounds(midi)
    notes = list(filter(lambda note: note.selected, take.notes))
    times = spread_times(notes, start_ppq, end_ppq)
    times_on_i, times_off_i = 0, 1
    for note in notes:
        note.start = take.ppq_to_time(times[times_on_i])
        note.end = take.ppq_to_time(times[times_off_i])
        times_on_i += 1
        times_off_i += 1


spread()
