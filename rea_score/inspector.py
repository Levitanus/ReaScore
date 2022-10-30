from copy import deepcopy
from enum import Enum
from pathlib import Path

from reapy_boost.core.reaper.reaper import perform_action

from rea_score.lily_convert import render_part

import reapy_boost as rpr
from reapy_boost import reascript_api as RPR
from typing import List, Optional, Union, cast

from reapy_boost.core.item.midi_event import CCShapeFlag
from rea_score.primitives import (Clef, GraceType, NotationEvent,
                                  NotationMarker, NotationPitch, Pitch)
from rea_score.notations_pitch import (
    NotationAccidental, NotationArticulation, NotationBeamGroupBegin,
    NotationBeamGroupEnd, NotationBeaming, NotationBreakBefore, NotationClef,
    NotationDynamics, NotationGhost, NotationGraceBegin, NotationGraceEnd,
    NotationIgnore, NotationSpacer, NotationStaffChange, NotationTrem,
    NotationTrill, NotationUnnormalizedLength, NotationVoice, NotationStaff,
    NotationXNoteBegin, NotationXNoteEnd)
from rea_score.notation_events import NotationKeySignature, NotationPlainText

from rea_score.scale import Accidental, Key, Scale

from .dom import (events_from_take, get_global_events, split_by_staff,
                  update_events, TrackPitchType, TrackType)
from .lily_convert import LyDict, render_staff
from .lily_export import render
from .keymap import keymap

EXT_SECTION = 'Levitanus_ReaScore'


class ProjectInspector:

    def __init__(self, project: Optional[rpr.Project] = None) -> None:
        if project is None:
            self.project = rpr.Project()
        else:
            self.project = project

    @property
    def export_dir(self) -> Path:
        if path := cast(Optional[Path], self.state('export_dir')):
            out = path
        else:
            path = Path('score')
        if not path.is_absolute():
            return path
        if not path.is_dir():
            out = path.parent.relative_to(self.project.path)
        else:
            out = path.relative_to(self.project.path)
        return out

    @export_dir.setter
    def export_dir(self, path: Path) -> None:
        if path.is_absolute():
            path = path.relative_to(Path(self.project.path))
        self.state('export_dir', path)

    @property
    def export_dir_absolute(self) -> Path:
        relative = self.export_dir
        path = Path(self.project.path).resolve()
        if not path.is_dir():
            path = path.parent
        return path.absolute().joinpath(relative)

    def state(self,
              key: str,
              value: Optional[object] = None) -> Optional[object]:
        state = self.project.get_ext_state(EXT_SECTION, 'main', pickled=True)
        if not state:
            state = {}
        if value is not None:
            state[key] = value  # type:ignore
            self.project.set_ext_state(EXT_SECTION,
                                       'main',
                                       state,
                                       pickled=True)
            return None
        return None if key not in state else state[key]  # type:ignore

    def ask_for_dynamics(self) -> str:
        ...

    @property
    def temp_pdf(self) -> Path:
        path = Path(self.project.path)
        if not path.is_dir():
            return path.parent.joinpath('temp.pdf')
        else:
            return path.joinpath('temp.pdf')

    def notations_at_start(self) -> List[NotationEvent]:
        # print('notations at start')
        notations: List[NotationEvent] = []
        if ks := cast(str, self.state('key_signature')):
            notations.append(NotationKeySignature.from_marker(ks))
        return notations

    @property
    def key_signature_at_start(self) -> Key:
        if ks := cast(str, self.state('key_signature')):
            return NotationKeySignature.from_marker(ks).key
        return Key('c', Scale.major)

    @key_signature_at_start.setter
    def key_signature_at_start(self, key: Key) -> None:
        self.state('key_signature', NotationKeySignature(key).for_marker())

    def place_key_signature_at_cursor(self, key: Key) -> rpr.Marker:
        pos = self.project.cursor_position
        name = NotationMarker.to_reaper_marker([NotationKeySignature(key)])
        return self.project.add_marker(pos, name, (0, 255, 0))

    def perform_shortcut(self, char: str) -> None:
        if char in keymap:
            func = keymap[char]
        else:
            func = ''
        print(char, func)
        if func:
            self.perform_func(func)

    @staticmethod
    def perform_func(func: str) -> None:
        eval(func)

    @property
    def score_tracks(self) -> List[rpr.Track]:
        score_guids = cast(Optional[List[str]], self.state('tracks')) or []
        pr_guids = {}
        for tr in self.project.tracks:
            pr_guids[tr.GUID] = tr
        tracks = []
        for guid in score_guids:
            if guid not in pr_guids:
                continue
            tracks.append(pr_guids[guid])
        return tracks

    @score_tracks.setter
    def score_tracks(self, tracks: List[rpr.Track]) -> None:
        self.state('tracks', list([tr.GUID for tr in tracks]))

    def score_track_add(self, track: rpr.Track) -> None:
        pr_tracks = [tr.GUID for tr in self.score_tracks]
        if track.GUID in pr_tracks:
            return
        pr_tracks.append(track.GUID)
        self.state('tracks', pr_tracks)

    def score_track_remove(self, track: rpr.Track) -> None:
        pr_tracks = [tr.GUID for tr in self.score_tracks]
        if track.GUID not in pr_tracks:
            return
        pr_tracks.remove(track.GUID)
        self.state('tracks', pr_tracks)

    def render_score(self) -> None:
        render_dicts = []
        for track in self.score_tracks:
            render_dicts.append(TrackInspector(track).render(compile_ly=False))
        return
        lily = render_score(render_dicts)
        export_path = self.export_dir_absolute
        export_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = render(lily, export_path)
        with open(pdf, 'rb') as in_:
            with open(ProjectInspector().temp_pdf, 'wb') as out:
                out.write(in_.read())
                out.truncate()


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
        state = self.track.project.get_ext_state(EXT_SECTION,
                                                 self.guid,
                                                 pickled=True)
        if not state:
            state = {}
        if value is not None:
            state[key] = value  # type:ignore
            self.track.project.set_ext_state(EXT_SECTION,
                                             self.guid,
                                             state,
                                             pickled=True)
            return None
        return None if key not in state else state[key]  # type:ignore

    def notations_at_start(self) -> List[NotationEvent]:
        notations: List[NotationEvent] = []
        if self.breakable_beam:
            notations.append(
                NotationPlainText("\n\\override Beam.breakable = ##t\n"))
        # if clef := self.clef:
        #     notations.append(NotationClef(Pitch(), clef))
        return notations

    @property
    def breakable_beam(self) -> bool:
        return cast(Optional[bool], self.state('breakable_beam')) or False

    @breakable_beam.setter
    def breakable_beam(self, value: bool) -> None:
        self.state('breakable_beam', value)

    @property
    def clef(self) -> Clef:
        return cast(Optional[Clef], self.state('clef')) or Clef.treble

    @clef.setter
    def clef(self, clef: Clef) -> None:
        self.state('clef', clef)

    @property
    def pitch_type(self) -> TrackPitchType:
        pt = self.state('pitch_type')
        if pt is None:
            return TrackPitchType.default
        return TrackPitchType(pt)

    @pitch_type.setter
    def pitch_type(self, pt: TrackPitchType) -> None:
        self.state('pitch_type', pt.value)

    @property
    def track_type(self) -> TrackType:
        pt = self.state('track_type')
        if pt is None:
            return TrackType.default
        return TrackType(pt)

    @track_type.setter
    def track_type(self, pt: TrackType) -> None:
        self.state('track_type', pt.value)

    @property
    def part_name(self) -> str:
        if name := self.state('part_name'):
            return name  # type:ignore
        if rpr.show_message_box(
                'Part name is not provided. Do You wish to use track name?',
                'part name dialog', 'ok-cancel') == 'ok':
            name = self.track.name
            self.state('part_name', name)
            return name
        else:
            try:
                # print('getting part name')
                name = rpr.get_user_inputs('Please, provide part name:',
                                           ['part name'])['part name']
                # print(f'got {name}')
                self.state('part_name', name)
                return name
            except RuntimeError:
                return ''

    @part_name.setter
    def part_name(self, name: str) -> None:
        self.state('part_name', name)

    @property
    def export_path(self) -> Path:
        dir_ = ProjectInspector().export_dir_absolute
        return dir_.joinpath(f"{self.part_name}.ly")

    @property
    def octave_offset(self) -> int:
        ofst = cast(Optional[int], self.state('octave_offset'))
        if ofst is None:
            ofst = 0
        return ofst

    @octave_offset.setter
    def octave_offset(self, ofst: int) -> None:
        self.state('octave_offset', ofst)

    def render(self, compile_ly: bool = True) -> LyDict:
        events = {}
        export_path = self.export_path
        begin, end = self.track.project.length, .0
        pitch_type = self.pitch_type
        note_names = []
        if pitch_type == TrackPitchType.note_names:
            note_names = self.track.midi_note_names
        for item in self.track.items:
            i_pos = item.position
            if begin > i_pos:
                begin = i_pos
            i_end = i_pos + item.length
            if end < i_end:
                end = i_end
            # print(f'update events by {item}')
            events.update(
                events_from_take(item.active_take, pitch_type, note_names))
        # print('getting global events')
        global_events = get_global_events([
            *ProjectInspector(self.track.project).notations_at_start(),
            *self.notations_at_start()
        ], begin, end)
        # events = update_events(events, global_events)
        events = {k: events[k] for k in sorted(events)}
        # print('sort staves')
        staves = split_by_staff(events)
        for staff in staves:
            # print(f'apply global events to staff {staff.staff_nr}')
            if (clef := self.clef) is not Clef.treble:
                staff.clef = clef
            staff.apply_global_events(global_events)
        # print(staves)
        # print('render part')
        lily_dict = render_part(self.part_name, staves, self.track_type,
                                self.octave_offset)
        lily = f'''{lily_dict['definition']}\n{lily_dict['expression']}'''
        export_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = render(lily, export_path, compile_ly)
        # while not pdf.exists():
        #     ...
        with open(pdf, 'rb') as in_:
            with open(ProjectInspector().temp_pdf, 'wb') as out:
                out.write(in_.read())
                out.truncate()
        ProjectInspector(self.track.project).score_track_add(self.track)
        return lily_dict


class NotationPitchInspector:

    def set(self, take: rpr.Take, notes: List[rpr.Note],
            events: List[NotationPitch]) -> None:
        midi = take.get_midi()
        notations = list(
            filter(lambda event: NotationPitch.is_reascore_event(event), midi))
        for note in notes:
            infos = note.infos
            channel = infos['channel']
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
                    for new in note_events:
                        if old.update(new) is True:
                            updated_events.append(new)
                parced.extend(
                    filter(lambda event: event not in updated_events,
                           note_events))
                note_events = parced
            buf = NotationPitch.to_midi_buf(note_events, Pitch(pitch), channel,
                                            original_buf)

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
@rpr.undo_block('set_accidental_for_selected_notes')
def set_accidental_for_selected_notes(accidental: Accidental) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationAccidental(Pitch(127), accidental)])


@rpr.inside_reaper()
@rpr.undo_block('set_voice_of_selected_notes')
def set_voice_of_selected_notes(voice: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationVoice(Pitch(127), voice)])


@rpr.inside_reaper()
@rpr.undo_block('set_channel_of_selected_notes')
def set_channel_of_selected_notes(channel: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    for note in selected:
        note.channel = channel


@rpr.inside_reaper()
@rpr.undo_block('set_staff_of_selected_notes')
def set_staff_of_selected_notes(staff: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationStaff(Pitch(127), staff)])


@rpr.inside_reaper()
@rpr.undo_block('set_staff_change_of_selected_notes')
def set_staff_change_of_selected_notes(staff: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationStaffChange(Pitch(127), staff)])


@rpr.inside_reaper()
@rpr.undo_block('set_clef_of_selected_notes')
def set_clef_of_selected_notes(clef: Clef) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))[0]
    NotationPitchInspector().set(editor.take, [selected],
                                 [NotationClef(Pitch(127), clef)])


@rpr.inside_reaper()
@rpr.undo_block('add_dynamics_at_selected_note')
def add_dynamics_at_selected_note(dyn: str = '') -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))[0]
    dynamics = dyn or rpr.get_user_inputs('type dynamics in lilypond format',
                                          ['dyn'])['dyn']
    NotationPitchInspector().set(editor.take, [selected],
                                 [NotationDynamics(Pitch(127), dynamics)])


@rpr.inside_reaper()
@rpr.undo_block('set_selected_notes_as_ghost')
def set_selected_notes_as_ghost() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationGhost(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('add_trill_to_selected_notes')
def add_trill_to_selected_notes() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationTrill(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('add_trem_to_selected_notes')
def add_trem_to_selected_notes(trem_denom: int) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationTrem(Pitch(127), trem_denom)])


@rpr.inside_reaper()
@rpr.undo_block('ignore_selected_notes')
def ignore_selected_notes() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationIgnore(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('unnormalize_selected_notes')
def unnormalize_selected_notes() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationUnnormalizedLength(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('make_selected_notes_spacers')
def make_selected_notes_spacers() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationSpacer(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('break_before_selected_notes')
def break_before_selected_notes() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = filter(lambda note: note.selected, notes)
    NotationPitchInspector().set(editor.take, list(selected),
                                 [NotationBreakBefore(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('spread_notes')
def spread_notes() -> None:
    aid = rpr.get_command_id("_RS7cecccb7cf0502b9821cfca8cbc8a621578c2293")
    if aid:
        rpr.perform_action(aid)


@rpr.inside_reaper()
@rpr.undo_block('view_score')
def view_score() -> None:
    aid = rpr.get_command_id("_RSb302ebd118f4823805e0a4c2c74e55ec2f4d8795")
    if aid:
        rpr.perform_action(aid)


@rpr.inside_reaper()
@rpr.undo_block('combine_items')
def combine_items() -> None:
    aid = rpr.get_command_id("_RS309e578f9acca56952277d83109c5d09cf3d70c0")
    if aid:
        rpr.perform_action(aid)


@rpr.inside_reaper()
@rpr.undo_block('grace_begin')
def grace_begin(grace_type: GraceType) -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))[0]
    NotationPitchInspector().set(
        editor.take, [selected],
        [NotationGraceBegin(Pitch(127), grace_type=grace_type)])


@rpr.inside_reaper()
@rpr.undo_block('grace_end')
def grace_end() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))[0]
    NotationPitchInspector().set(editor.take, [selected],
                                 [NotationGraceEnd(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('set_x_notes_to_selected')
def set_x_notes_to_selected(dyn: str = '') -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))
    first, last = selected[0], selected[-1]
    NotationPitchInspector().set(editor.take, [first],
                                 [NotationXNoteBegin(Pitch(127))])
    NotationPitchInspector().set(editor.take, [last],
                                 [NotationXNoteEnd(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('make_beam_group_from_selected_notes')
def make_beam_group_from_selected_notes(dyn: str = '') -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))
    first, last = selected[0], selected[-1]
    NotationPitchInspector().set(editor.take, [first],
                                 [NotationBeamGroupBegin(Pitch(127))])
    NotationPitchInspector().set(editor.take, [last],
                                 [NotationBeamGroupEnd(Pitch(127))])


@rpr.inside_reaper()
@rpr.undo_block('add_articulation_to_selected_notes')
def add_articulation_to_selected_notes(art: str = '',
                                       position: str = '-') -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))
    articulation = art or rpr.get_user_inputs(
        'type articulation in lilypond format', ['art'])['art']
    NotationPitchInspector().set(
        editor.take, selected,
        [NotationArticulation(Pitch(127), articulation, position)])


@rpr.inside_reaper()
@rpr.undo_block('custom_beaming_for_selected_notes')
def custom_beaming_for_selected_notes() -> None:
    ptr = RPR.MIDIEditor_GetActive()  # type:ignore
    if not rpr.is_valid_id(ptr):
        return
    editor = rpr.MIDIEditor(ptr)
    notes = editor.take.notes
    selected = list(filter(lambda note: note.selected, notes))
    inputs = rpr.get_user_inputs(
        ('type beaming lists in lilypond format, for example:\n'
         '0 1 | 0 1 2\n'
         'for making left part look like 16th and right part like 32nd.\n'
         'type no value for single beam.'), ['left', 'right'])

    NotationPitchInspector().set(
        editor.take, selected,
        [NotationBeaming(Pitch(127), inputs['left'], inputs['right'])])
