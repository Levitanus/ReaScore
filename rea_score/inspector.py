from pathlib import Path
# import time
# from shutil import copyfile

import reapy as rpr
from typing import Optional, Tuple, Union

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
            return path
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
            state[key] = value
            return None
        return None if key not in state else state[key]

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
            state[key] = value
            self.track.project.set_ext_state(
                EXT_SECTION, self.guid, state, pickled=True
            )
            return None
        return None if key not in state else state[key]

    @property
    def part_name(self) -> str:
        if name := self.state('part_name'):
            return name
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
            print(item.track, item.track.name, item)
            events.update(events_from_take(item.active_take))
        print(events)
        lily = render_staff(split_by_voice(events))
        pdf = render(lily, export_path)
        print(pdf, ProjectInspector().temp_pdf)
        while not pdf.exists():
            ...
        # copyfile(str(pdf), str(ProjectInspector().temp_pdf))
        with open(pdf, 'rb') as in_:
            with open(ProjectInspector().temp_pdf, 'wb') as out:
                out.write(in_.read())
                out.truncate()
