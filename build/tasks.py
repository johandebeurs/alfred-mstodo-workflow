import os
from invoke import Collection, task
import subtasks

@task
def clean(c):
    subtasks.clean(c)

@task(pre=[clean])
def build(c, initial=False):
    print("Running build sequence:")
    subtasks.minify(c)
    subtasks.copy_libs(c, initial=initial)
    subtasks.copy(c)
    subtasks.symlink(c)
    subtasks.replace(c)
    subtasks.package_workflow(c)
    subtasks.package_workflow(c, env="dev")

@task
def watch(c, changed_files=None):
    # if there are changes in the /src directory, then re-run the build-dev tasks
    # this means re-copy relevant files to destination and recreate the workflow
    print("Watching files for changes:")
    if changed_files is None:
        from watchfiles import watch
        for changes in watch('./src', './screenshots','./changelog.md', './README.md'):
            changed_files = [change[1].removeprefix(os.getcwd() + '/') for change in changes] # unpacks the set of FileChanges into a list of absolute paths
            watch(c, changed_files=changed_files)
    
    subtasks.minify(c,changed_files=changed_files)
    subtasks.copy(c,changed_files=changed_files)
    subtasks.replace(c)
    subtasks.package_workflow(c, rebuild=True)
    return

@task(pre=[build])
def release(c):
    print("Releasing version onto github:")
    subtasks.release(c)

@task
def test(c):
    print("Running Pytest")
    subtasks.test(c)

namespace = Collection(clean, build, watch, release, test, subtasks)
