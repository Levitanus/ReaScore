keymap = {
    # voices
    "1": 'set_voice_of_selected_notes(1)',
    "2": 'set_voice_of_selected_notes(2)',
    "3": 'set_voice_of_selected_notes(3)',
    "4": 'set_voice_of_selected_notes(4)',
    "!": 'set_channel_of_selected_notes(0)',
    "@": 'set_channel_of_selected_notes(1)',
    "#": 'set_channel_of_selected_notes(2)',
    "$": 'set_channel_of_selected_notes(3)',
    # staves
    "[": 'set_staff_of_selected_notes(1)',
    "]": 'set_staff_of_selected_notes(2)',
    "{": 'set_staff_change_of_selected_notes(1)',
    "}": 'set_staff_change_of_selected_notes(2)',
    # clefs
    't': 'set_clef_of_selected_notes(Clef.treble)',
    'T': 'set_clef_of_selected_notes(Clef.tenor)',
    'a': 'set_clef_of_selected_notes(Clef.alto)',
    'C': 'set_clef_of_selected_notes(Clef.bass)',
    'p': 'set_clef_of_selected_notes(Clef.percussion)',
    # accidentals
    '=': 'set_accidental_for_selected_notes(Accidental.is_)',
    '-': 'set_accidental_for_selected_notes(Accidental.es)',
    '+': 'set_accidental_for_selected_notes(Accidental.isis)',
    '_': 'set_accidental_for_selected_notes(Accidental.es)',
    '0': 'set_accidental_for_selected_notes(Accidental.white)',
    # misc
    '`': 'add_trill_to_selected_notes()',
    '~': 'ignore_selected_notes()',
    '?': 'unnormalize_selected_notes()',
    'g': 'set_selected_notes_as_ghost()',
    'r': 'TrackInspector().render()',
    'S': 'make_selected_notes_spacers()',
    's': 'spread_notes()',
    'v': 'view_score()',
    'c': 'combine_items()',
    'e': 'add_dynamics_at_selected_note()',
    'E': 'add_dynamics_at_selected_note("!")',
    'B': 'custom_beaming_for_selected_notes()',
    'b': 'make_beam_group_from_selected_notes()',
    '\\': 'break_before_selected_notes()',
    # grace
    # TODO: make one-hotkey
    'g': 'grace_begin(GraceType.grace)',
    'a': 'grace_begin(GraceType.acciaccatura)',
    'A': 'grace_begin(GraceType.appoggiatura)',
    'G': 'grace_end()',
    # articulations
    '-': 'add_articulation_to_selected_notes()',
    '*': 'add_articulation_to_selected_notes(position="^")',
    '/': 'add_articulation_to_selected_notes(position="_")',
    'x': 'set_x_notes_to_selected()'
}

funcmap = {v: k for k, v in keymap.items()}
