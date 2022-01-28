import reapy as rpr
import rea_score.inspector as it


def render_selected_track() -> None:
    track = rpr.Project().selected_tracks[0]
    it.TrackInspector().render()


render_selected_track()
print("end")
