from os import system
import subprocess
import re
from pathlib import Path
import textwrap
from typing import List

# from .lily_convert import any_to_lily


def lily_version() -> str:
    """Get version string of installed lilypond.

    Returns
    -------
    str
        e.g. '\\version x.xx.x'

    Raises
    ------
    RuntimeError
        if something went wrong
    """
    result = subprocess.check_output(['lilypond', '--version']).split(b'\n')
    if m := re.search(r'(\d+\.\d+\.\d+)', str(result[0])):
        version = m.groups()[0]
    else:
        raise RuntimeError(f'Lily version not found: {result}')
    return f'\\version "{version}"'


def line_strip(line: str) -> str:
    return re.sub(r'(\s\s)|\n', ' ', line)


def format_lines(lilypond: str) -> List[str]:
    patterns = {
        re.compile(r'<<(?!\n)'): '<<\n',
        re.compile(r'{(?!\n)'): '{\n',
        re.compile(r'(?!\n)>>'): '\n>>',
        re.compile(r'(?!\n)}'): '\n}',
        re.compile(r'(?=\s)\|(?=\s)'): '|\n',
    }
    idents = re.compile(r'(<<)|{')
    dedents = re.compile(r'(>>)|}')
    for pattern, repl in patterns.items():
        lilypond = re.sub(pattern, repl, lilypond)
    lines = re.split(r'\n', lilypond)
    out = []
    ident = 0
    ident_am = 4
    for line in lines:
        line = line_strip(line)
        if m := re.search(dedents, line):
            ident -= 1
        # if line:
        ident_str = ' ' * ident
        ident_level = ident_str * ident_am
        wraped = textwrap.wrap(
            line,
            width=80 - len(ident_level + ident_str),
            subsequent_indent=ident_level + ident_str,
            # initial_indent=ident_level
        )
        out.append(ident_level + '\n'.join(wraped))
        if m := re.search(idents, line):
            ident += 1
    return out


def render(lilypond: str, file: Path, compile_ly: bool = True) -> Path:
    ver = lily_version()
    string = f'{ver}\n{lilypond}'
    lines = format_lines(string)
    ly = file.with_suffix('.ly')
    with open(ly, 'w') as io:
        io.write('\n'.join(lines))
    # print(subprocess.check_output(['lilypond', str(ly)]))
    pdf = file.with_suffix('.pdf')
    if compile_ly:
        process = subprocess.Popen(['lilypond', str(ly)], cwd=pdf.parent)
        process.wait()
    return pdf


# if __name__ == '__main__':
# lily_string = """    {\\new Staff <<\
#     \\new Voice {r1 | r1 | r8 cis''8. b'8.~ <dis''~ b'>16 <dis''>8 fis''16 \
#     <fis''~ b''>16 <fis'' cis'''~>32 cis'''32 b''8 | }>>}"""
# import reapy_boost as rpr
# with rpr.inside_reaper():
#     lily_string = any_to_lily(rpr.Project().selected_items[0].active_take)
# # print(lily_string)
# print(lily_version())
# print(render(lily_string, Path("/home/levitanus/gits/ReaScore/test.ly")))
