import reapy_boost as rpr
from pprint import pprint

midi = rpr.Project().selected_items[0].active_take.get_midi()
notations = filter(lambda event: event['selected'], midi)

pprint(list(bytes(not_['buf'][2:]).decode('latin-1') for not_ in notations))