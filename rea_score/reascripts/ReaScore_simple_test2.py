import reapy as rpr

from pprint import pprint

pr = rpr.Project()

with rpr.inside_reaper():
    for track in pr.tracks:
        # reveal_type(track)
        print(track.name, track.depth, track.parent_track)
