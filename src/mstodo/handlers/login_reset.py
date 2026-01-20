from workflow.notify import notify
from mstodo import auth, icons
from mstodo.util import wf_wrapper

wf = wf_wrapper()

def display(args):
    new_args = ' '.join(args)
    if not '--commit' in new_args:
        new_args = '--commit'
    wf.add_item(
        'Are you sure?',
        'Your login will be recreated',
        arg=new_args,
        valid=True,
        icon=icons.CHECKMARK
    )

    wf.add_item(
        'Never mind',
        autocomplete='',
        icon=icons.CANCEL
    )

def commit(args, modifier=None):
    auth.deauthorise()
    wf.clear_data()
    wf.clear_cache()

    notify(title='Authentication', message='You are now logged out')
    auth.authorise()
    notify(title='Authentication', message='login successful')