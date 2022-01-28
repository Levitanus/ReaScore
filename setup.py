from distutils.core import setup

setup(
    name='rea_score',
    version='0.1',
    description='LilyPond and musicXml exporter for Reaper',
    author='Levitanus',
    author_email='pianoist@ya.ru',
    # entry_points={
    #     'console_scripts': ['sample_editor = sample_editor.__main__:main']
    # },
    packages=['rea_score'],  # same as name
    package_data={'rea_score': ['py.typed']},
    # install_requires=['reapy-boost @ git+https://github.com/Levitanus/reapy-boost.git'],
)
