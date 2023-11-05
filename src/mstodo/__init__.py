import os

__title__ = 'Alfred-MSToDo'
with open(os.path.join(os.path.dirname(__file__), '../version'), encoding='ASCII') as fp:
    __version__ = fp.read()
__author__ = 'Johan de Beurs, Ian Paterson'
__licence__ = 'MIT'
__copyright__ = 'Copyright 2023 Johan de Beurs, 2013-2017 Ian Paterson'
__githubslug__ = 'johandebeurs/alfred-mstodo-workflow'

def get_version():
    return __version__

def get_github_slug():
    return __githubslug__