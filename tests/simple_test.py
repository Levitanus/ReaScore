from rea_score import inspector as it
import reapy as rpr

take = rpr.Project().selected_items[0].active_take
print(it.Notation().get(take, take.notes[0])[0].accidental)
