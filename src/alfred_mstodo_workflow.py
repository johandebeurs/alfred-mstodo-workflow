#!/usr/bin/env python3
# encoding: utf-8

import sys

def main(workflow) -> None:
    log = workflow.logger
    route(workflow.args)  # pylint: disable=E0606
    log.info(f"Workflow response complete with args {workflow.args}") # pylint: disable=E0606

if __name__ == '__main__':
    from mstodo.util import wf_wrapper
    from mstodo.handlers.route import route

    # Create Workflow instance
    wf = wf_wrapper()

    sys.exit(wf.run(main, text_errors='--commit' in wf.args))
