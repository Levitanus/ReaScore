import reapy as rpr
import rea_score.inspector as it


@rpr.inside_reaper()
def render_selected_track() -> None:
    track = rpr.Project().selected_tracks[0]
    it.TrackInspector().render()


render_selected_track()
print("end")
