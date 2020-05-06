#!/usr/bin/python
# encoding: utf-8

import logging
from logging.config import fileConfig
import sys

fileConfig('logging_config.ini')

from mstodo.handlers.route import route
from mstodo.util import workflow

log = logging.getLogger('mstodo')

def main(wf):
    route(wf.args)
    log.info('Workflow response complete')

if __name__ == '__main__':
    wf = workflow()
    sys.exit(wf.run(main, text_errors='--commit' in wf.args))