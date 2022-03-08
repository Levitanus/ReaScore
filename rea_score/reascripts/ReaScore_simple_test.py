import reapy_boost as rpr

import reapy_boost as rpr
from reapy_boost import reascript_api as RPR
from rea_score.primitives import Position
from pprint import pprint
from reapy_boost import reascript_api as RPR
from reapy_boost import ImGui

take = rpr.Project().selected_items[0].active_take
midi = take.get_midi()
pprint(midi)

notations = filter(lambda d: d['buf'][0] == 0xff, midi)
pprint(
    list(
        (
            Position(take.ppq_to_beat(ev['ppq'])),
            bytes(ev['buf'][2:]).decode('latin-1')
        ) for ev in notations
    )
)
