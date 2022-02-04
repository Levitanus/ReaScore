# print('import reapy as rpr')
import reapy as rpr

# print('import rea_score.inspector as it')
import rea_score.inspector as it


@rpr.inside_reaper()
def render_selected_track() -> None:
    track = rpr.Project().selected_tracks[0]
    it.TrackInspector().render()


# print('render')
render_selected_track()
# print("end")
