from workflow.notify import notify
from mstodo import auth, icons
from mstodo.util import wf_wrapper

wf = wf_wrapper()

def filter(args):
    wf.add_item(
        'Are you sure?',
        'You will need to log in to a Microsoft account to continue using the workflow',
        arg=' '.join(args),
        valid=True,
        icon=icons.CHECKMARK
    )

    wf.add_item(
        'Nevermind',
        autocomplete='',
        icon=icons.CANCEL
    )

def commit(args, modifier=None):
    auth.deauthorise()
    wf.clear_data()
    wf.clear_cache()

    notify(title='Authentication', message='You are now logged out')
