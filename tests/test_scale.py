from rea_score import scale as sc


def test_accidental() -> None:
    assert sc.Accidental.from_str('♯') == sc.Accidental.is_
    assert sc.Accidental.from_str('♯♯') == sc.Accidental.isis
    assert sc.Accidental.from_str('♭') == sc.Accidental.es
    assert sc.Accidental.from_str('♭♭') == sc.Accidental.eses
    assert sc.Accidental.from_str('') == sc.Accidental.white


def test_pitch_resolver() -> None:
    a_moll = sc.Key('a', sc.Scale.minor)
    a_dur = sc.Key('a', sc.Scale.major)

    d_moll = sc.Key('d', sc.Scale.minor)
    d_dur = sc.Key('d', sc.Scale.major)

    fis_moll = sc.Key('fis', sc.Scale.minor)
    fis_dur = sc.Key('fis', sc.Scale.major)

    ais_dur = sc.Key('ais', sc.Scale.major)
    des_moll = sc.Key('des', sc.Scale.minor)

    # first test against idiot mistake:
    assert sc.midi_to_note(60, sc.Key('c', sc.Scale.major)) == 'c4'

    # test on Bb3
    midi = 58
    assert sc.midi_to_note(midi, d_moll) == 'b♭3'
    # test against major alteration (VI♭)
    assert sc.midi_to_note(midi, d_dur) == 'b♭3'

    # test against minor alteration (II♭)
    assert sc.midi_to_note(midi, a_moll) == 'b♭3'
    assert sc.midi_to_note(midi, a_dur) == 'a♯3'
    assert sc.midi_to_note(midi, a_dur, sc.Accidental.es) == 'b♭3'

    assert sc.midi_to_note(midi, fis_moll) == 'a♯3'
    assert sc.midi_to_note(midi, fis_dur) == 'a♯3'

    # test against tonality doublesharps and doubleflats
    assert sc.midi_to_note(62, ais_dur) == 'c♯♯4'
    assert sc.midi_to_note(57, des_moll) == 'b♭♭3'

    # some church scales
    c_phrygian = sc.Key('c', sc.Scale.phrygian)
    assert sc.midi_to_note(61, c_phrygian) == 'd♭4'
    assert sc.midi_to_note(63, c_phrygian) == 'e♭4'
    assert sc.midi_to_note(65, c_phrygian) == 'f4'

    fis_dorian = sc.Key('fis', sc.Scale.dorian)
    assert sc.midi_to_note(60, fis_dorian) == 'b♯3'

    # test against known bugs
    assert sc.midi_to_note(64, fis_dur) == 'e4'
    assert sc.midi_to_note(62, fis_dur) == 'd4'
