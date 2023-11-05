#!/usr/bin/env python3
# encoding: utf-8

import sys
import logging
from os import path
from logging.config import fileConfig

ROOT_DIR = path.dirname(path.abspath(__file__))
fileConfig(path.join(ROOT_DIR,"logging_config.ini"))
log = logging.getLogger('mstodo')

def main(workflow):
    route(workflow.args)
    log.info(f"Workflow response complete with args {workflow.args}")

if __name__ == '__main__':
    from mstodo.util import wf_wrapper
    from mstodo.handlers.route import route

    wf = wf_wrapper()
    sys.exit(wf.run(main, text_errors='--commit' in wf.args))
