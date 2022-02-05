from typing import cast
import reapy as rpr
from rea_score import inspector as it
from reapy import ImGui
from rea_score.dom import TrackPitchType, TrackType

from rea_score.scale import Key, Scale
from rea_score.primitives import Pitch
from rea_score.keymap import keymap, funcmap

ctx = ImGui.CreateContext('ReaScore', ImGui.ConfigFlags_DockingEnable())
# font_path = Path(__file__).parent.parent.joinpath('Montserrat-Regular.ttf')
# print(font_path, font_path.exists())
font = ImGui.CreateFont('Montserrat', 14)
ImGui.AttachFont(ctx, font)

proj_insp = it.ProjectInspector()

key_signature = {'tonic': 'c', 'scale': Scale.major}


def key_signatures() -> None:
    # ImGui.TreePush(ctx, 'key_signatures')
    rt = ImGui.TreeNode(ctx, 'key signatures')
    if not rt:
        return
    # ImGui.BeginGroup(ctx)
    ImGui.Text(ctx,
               f"From the start: {proj_insp.key_signature_at_start.as_str()}")
    ImGui.SetNextItemWidth(ctx, 30)
    rt, buf = ImGui.InputText(ctx, 'tonic', key_signature['tonic'], 10)
    if rt:
        key_signature['tonic'] = buf

    ImGui.SameLine(ctx)
    ImGui.SetNextItemWidth(ctx, 100)

    rt = ImGui.BeginCombo(ctx, 'scale', key_signature['scale'].value)
    if rt:
        for sc in Scale:
            s_rt, selected = ImGui.Selectable(ctx, sc.value, 0)
            if selected:
                key_signature['scale'] = Scale(sc)
        ImGui.EndCombo(ctx)
    rt = ImGui.Button(ctx, 'to start')
    if rt:
        proj_insp.key_signature_at_start = Key(key_signature['tonic'],
                                               key_signature['scale'])
    ImGui.SameLine(ctx)
    rt = ImGui.Button(ctx, 'at the cursor')
    if rt:
        proj_insp.place_key_signature_at_cursor(
            Key(key_signature['tonic'], key_signature['scale']))

    ImGui.TreePop(ctx)


def track_inspector() -> None:
    rt = ImGui.TreeNode(ctx, 'Track Inspector')
    if not rt:
        return
    track = rpr.Project().selected_tracks[0]
    ti = it.TrackInspector(track)
    if track in proj_insp.score_tracks:
        part_name = ti.part_name
    else:
        part_name = 'not rendered'
    ImGui.Text(ctx, '"{n}"; part name: "{p}"'.format(n=track.name,
                                                     p=part_name))
    ImGui.SameLine(ctx)
    rt = ImGui.Button(ctx, 'render')
    if rt:
        ti.render()

    ImGui.SetNextItemWidth(ctx, 100)
    rt = ImGui.BeginCombo(ctx, 'pitch type', ti.pitch_type.value)
    if rt:
        for pt in TrackPitchType:
            rt, v = ImGui.Selectable(ctx, pt.value, False)
            if v:
                ti.pitch_type = pt
        ImGui.EndCombo(ctx)

    ImGui.SetNextItemWidth(ctx, 100)
    rt = ImGui.BeginCombo(ctx, 'track type', ti.track_type.value)
    if rt:
        for pt in TrackType:
            rt, v = ImGui.Selectable(ctx, pt.value, False)
            if v:
                ti.track_type = pt
        ImGui.EndCombo(ctx)

    ImGui.TreePop(ctx)


def actions() -> None:
    rt = ImGui.TreeNode(ctx, 'Tools')
    if not rt:
        return

    color = 0x00ff00ff
    ImGui.TextColored(ctx, color, 'Voices:')
    for i in range(1, 5):
        if i > 1:
            ImGui.SameLine(ctx)
        func = f'set_voice_for_selected_notes({i})'
        text = str(i)
        if func in funcmap:
            text += f" ({funcmap[func]})"
        rt = ImGui.Button(ctx, text, 20)
        if rt:
            proj_insp.perform_func(func)

    ImGui.TreePop(ctx)


class DockWidget:
    def __init__(self, ctx: object,
                 project_inspector: it.ProjectInspector) -> None:
        self.ctx = ctx
        self.ins = project_inspector
        self.state = cast(int, self.ins.state('GUI_dockstate')) or 0
        self.flags = self.flags_from_State(self.state)
        self.dock_id = self.ins.state('GUI_dockid') or 0
        self.dock_changed = bool(self.state)

    def flags_from_State(self, state: int) -> int:
        if state:
            return 0
        return ImGui.WindowFlags_NoDocking()

    def frame(self) -> None:
        if self.state:
            self.dock_id = ImGui.GetWindowDockID(self.ctx)
            self.ins.state('GUI_dockid', self.dock_id)
        rt, self.state = ImGui.Checkbox(self.ctx, 'dock', self.state)
        if not rt:
            return
        self.ins.state('GUI_dockstate', self.state)
        self.dock_changed = True
        self.flags = self.flags_from_State(self.state)

    def before_begin(self) -> int:
        if not self.dock_changed:
            return self.flags
        self.dock_changed = False
        if self.state:
            if self.dock_id == 0:
                self.dock_id = -2
        ImGui.SetNextWindowDockID(self.ctx, self.dock_id)
        return self.flags


def view_score() -> None:
    rt = ImGui.Button(ctx, 'view score')
    if rt:
        aid = rpr.get_command_id("_RSb302ebd118f4823805e0a4c2c74e55ec2f4d8795")
        if aid is None:
            rpr.show_message_box('add ReaScore reascripts to Reaper')
        else:
            rpr.perform_action(aid)


dock = DockWidget(ctx, proj_insp)


def loop() -> None:
    ImGui.PushFont(ctx, font)
    window_flags = dock.before_begin()
    # print(window_flags, ImGui.WindowFlags_AlwaysAutoResize())
    window_flags |= ImGui.WindowFlags_AlwaysAutoResize()
    visible, opened = ImGui.Begin(ctx, 'ReaScore', True, window_flags)

    if visible:
        dock.frame()
        ImGui.SameLine(ctx, spacingInOptional=40)
        view_score()
        key_signatures()

        track_inspector()
        actions()

    ImGui.PopFont(ctx)
    if visible:
        ImGui.End(ctx)

    if opened:
        rpr.defer(loop)
    else:
        ImGui.DestroyContext(ctx)


rpr.defer(loop)
