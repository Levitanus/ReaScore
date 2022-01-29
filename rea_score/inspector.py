from copy import deepcopy
from pathlib import Path

import reapy as rpr
from reapy import reascript_api as RPR
from typing import List, Optional, Union, cast

from reapy.core.item.midi_event import CCShapeFlag
from rea_score.primitives import NotationAccidental, NotationEvent, NotationPitch, NotationVoice, Pitch

from rea_score.scale import Accidental

from .dom import events_from_take, split_by_voice
from .lily_convert import render_staff
from .lily_export import render

EXT_SECTION = 'Levitanus_ReaScore'


class ProjectInspector:

    def __init__(self, project: Optional[rpr.Project] = None) -> None:
        if project is None:
            self.project = rpr.Project()
        else:
            self.project = project

    @property
    def export_dir(self) -> Path:
        if path := self.state('export_dir'):
            return path  # type:ignore
        path = Path(self.project.path)
        if not path.is_dir():
            return path.parent
        else:
            return path

    def state(self,
              key: str,
              value: Optional[object] = None) -> Optional[object]:
        state = self.project.get_ext_state(EXT_SECTION, 'main', pickled=True)
        if not state:
            state = {}
        if value is not None:
            state[key] = value  # type:ignore
            return None
        return None if key not in state else state[key]  # type:ignore

    @property
    def temp_pdf(self) -> Path:
        path = Path(self.project.path)
        if not path.is_dir():
            return path.parent.joinpath('temp.pdf')
        else:
            return path.joinpath('temp.pdf')


class TrackInspector:

    def __init__(self, track: Optional[Union[rpr.Track, str]] = None) -> None:
        if track is None:
            self.track = rpr.Project().selected_tracks[0]
        elif isinstance(track, str):
            self.track = rpr.Track.from_GUID(track)
        else:
            self.track = track
        self.guid = self.track.GUID

    def state(self,
              key: str,
              value: Optional[object] = None) -> Optional[object]:
        state = self.track.project.get_ext_state(
            EXT_SECTION, self.guid, pickled=True
        )
        if not state:
            state = {}
        if value is not None:
            state[key] = value  # type:ignore
            self.track.project.set_ext_state(
                EXT_SECTION, self.guid, state, pickled=True
            )
            return None
        return None if key not in state else state[key]  # type:ignore

    @property
    def part_name(self) -> str:
        if name := self.state('part_name'):
            return name  # type:ignore
        if rpr.show_message_box(
            'Part name is not provided. Do You wish to use track name?',
            'part name dialog', 'ok-cancel'
        ) == 'ok':
            name = self.track.name
            self.state('part_name', name)
            return name
        else:
            try:
                name = rpr.get_user_inputs(
                    'Please, provide part name:', ['part name']
                )['part name']
                self.state('part_name', name)
                return name
            except RuntimeError:
                exit()

    @property
    def export_path(self) -> Path:
        dir_ = ProjectInspector().export_dir
        return dir_.joinpath(f"{self.part_name}.ly")

    def render(self) -> None:
        events = {}
        export_path = self.export_path
        for item in self.track.items:
            events.update(events_from_take(item.active_take))
        lily = render_staff(split_by_voice(events))
        pdf = render(lily, export_path)
        while not pdf.exists():
            ...
        with open(pdf, 'rb') as in_:
            with open(ProjectInspector().temp_pdf, 'wb') as out:
                out.write(in_.read())
                out.truncate()


class NotationPitchInspector:

    def set(
        self, take: rpr.Take, notes: List[rpr.Note],
        events: List[NotationPitch]
    ) -> None:
        midi = take.get_midi()
        notations = list(
            filter(lambda event: NotationPitch.is_reascore_event(event), midi)
        )
        for note in notes:
            infos = note.infos
            ppq = infos['ppq_position']
            pitch = infos['pitch']
            note_events = deepcopy(events)
            original_buf = None
            for note_event in note_events:
                note_event.pitch = Pitch(pitch)
            updated_events = []
            for notation in notations:
                if notation['ppq'] != ppq:
                    continue
                parced = NotationPitch.from_midibuf(notation['buf'])
                if not parced:
                    continue
                if parced[0].pitch.midi_pitch != pitch:
                    continue
                original_buf = notation['buf']
                for old in parced:
                    updated = False
                    for new in note_events:
                        if old.update(new) is True:
                            updated = True
                            updated_events.append(new)
                parced.extend(
                    filter(
                        lambda event: event not in updated_events, note_events
                    )
                )
                note_events = parced
            buf = NotationPitch.to_midi_buf(
                note_events, Pitch(pitch), original_buf
            )

            event = rpr.MIDIEventDict(
                ppq=ppq,
                buf=buf,
                cc_shape=CCShapeFlag.linear,
                muted=False,
                selected=False,
            )
            midi.append(event)
        midi = sorted(midi, key=lambda d: d['ppq'])
        take.set_midi(midi, sort=True)


@rpr.inside_reaper()
def set_accidental_for_selected_notes(accidental: Accidental) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(
        editor.take, list(selected),
        [NotationAccidental(Pitch(127), accidental)]
    )


@rpr.inside_reaper()
def set_voice_of_selected_notes(voice: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(
        editor.take, list(selected), [NotationVoice(Pitch(127), voice)]
    )
