from reapy import ImGui
import reapy as rpr
from rea_score.inspector import ProjectInspector

ctx = ImGui.CreateContext('getkey', True)


def loop() -> None:
    vis, opened = ImGui.Begin(ctx, 'getkey')
    ImGui.CaptureKeyboardFromApp(ctx, True)
    captured, char = ImGui.GetInputQueueCharacter(ctx, 0)
    if captured:
        ProjectInspector().perform_shortcut(chr(char))
        vis = False
    ImGui.End(ctx)

    if vis:
        rpr.defer(loop)
    else:
        ImGui.DestroyContext(ctx)


rpr.defer(loop)
