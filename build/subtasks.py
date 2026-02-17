import paths
import os, sys
import glob
import tomllib
from invoke import task

def get_metadata_from_pyproject():
    """Extract all metadata from pyproject.toml

    Returns:
        dict: Dictionary containing all metadata fields
    """
    pyproject_path = os.path.join(os.path.dirname(__file__), '../pyproject.toml')
    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)

    project = data['project']
    tool_metadata = data.get('tool', {}).get('alfred-mstodo', {})

    # Extract authors as comma-separated string
    authors = ', '.join(author.get('name', '') for author in project.get('authors', []))

    # Extract github slug from repository URL
    repo_url = project.get('urls', {}).get('Repository', '')
    github_slug = repo_url.replace('https://github.com/', '')

    return {
        'version': project['version'],
        'title': tool_metadata.get('title', 'Alfred-MSToDo'),
        'author': authors,
        'license': project.get('license', {}).get('text', 'MIT'),
        'copyright': tool_metadata.get('copyright', ''),
        'githubslug': github_slug
    }

@task
def clean(c):
    print(" Removing distribution, temp and local log files...")
    workflow_log_files = glob.glob(f"../**/workflow*.log*", recursive=True)
    c.run(f"rm -rf {paths.dist}")
    c.run(f"rm -rf {paths.tmp}")
    c.run(f"rm -f {paths.dist_workflow}")
    c.run(f"rm -f {paths.dist_workflow_symlinked}")
    for log_file in workflow_log_files:
        c.run(f"rm {log_file}")
    return

@task
def minify(c, changed_files=None):
    # copies and minifies /src/icons/icon.png into /dist/workflow/icon.png
    # copies and minifies /src/icons/*/**/*.png into /dist/workflow/icons/**/.png
    c.run("mkdir -p {}/{{dark,light}}".format(paths.tmp_img))
    images = glob.glob(f"{paths.app_icons}/**/*.png", recursive=True)
    if changed_files: images = list(set(images) & set(changed_files))
    print(" Compressing {}images...".format(str(len(images)) + " "))
    for img in images:
        dest = paths.tmp_img + img.removeprefix(paths.app_icons)
        c.run(f"sips -o {dest} -Z 100 {img} >/dev/null")
    return

@task()
def copy(c, changed_files=None):
    print(" Copying app files for distribution...")
    icons = glob.glob(f"{paths.tmp_img}/**/*.png", recursive=True)
    if changed_files: icons = list(set(icons) & set(changed_files))
    for icon in icons:
        if icon == f"{paths.tmp_img}/icon.png":
            dest = f"{paths.dist_app}/icon.png"
        else:
            dest = paths.dist_icons + icon.removeprefix(paths.tmp_img)
        c.run(f"ditto {icon} {dest}")

    # Copy *.scpt in paths.app_bin to paths.dist_bin
    bin_files = glob.glob(f"{paths.app_bin}/*.scpt")
    if changed_files: bin_files = list(set(bin_files) & set(changed_files))
    for bin_file in bin_files:
        dest = paths.dist_bin + bin_file.removeprefix(paths.app_bin)
        c.run(f"ditto {bin_file} {dest}")

    app_files = glob.glob(f"{paths.app_module}/**/*.py", recursive=True)
    app_files.extend(glob.glob(f"{paths.app}/*.py"))
    app_files.extend(glob.glob(f"{paths.app}/*.ini"))
    # app_files.extend(glob.glob(f"{paths.app}/version"))
    if changed_files: app_files = list(set(app_files) & set(changed_files))
    for app_file in app_files:
        dest = paths.dist_app + app_file.removeprefix(paths.app_dirname)
        c.run(f"ditto {app_file} {dest}")
    
    print(" Copied {}files...".format(str(len(icons) + len(bin_files) + len(app_files)) + " "))
    return

@task()
def copy_libs(c, initial=False):
    print(" Copying module dependencies...")
    lib_files = []
    lib_files.extend(glob.glob(f"{paths.app_lib}/**/*.py", recursive=True))
    lib_files.extend(glob.glob(f"{paths.app_lib}/**/*.pem", recursive=True))
    lib_files.extend(glob.glob(f"{paths.app_lib}/**/version"))
    lib_files.sort()
    for lib_file in lib_files:
        c.run(f"ditto {lib_file} {paths.dist_lib}{str(lib_file).removeprefix(paths.app_lib)}")
    if initial:
        print("  Cloning alfred workflow into /src")
        for workflow_file in glob.glob(f"{paths.app_lib}/workflow/*", recursive=True):
            c.run(f"ditto {workflow_file} {paths.app}{str(workflow_file).removeprefix(paths.app_lib)}")
    return

@task()
def symlink(c):
    print(" Creating symbolic links for dev workflow...")
    # take relevant files in cwd/paths.dist_app and symlink to paths.tmp_workflow_symlinked
    c.run(f"mkdir -p {paths.tmp_workflow_symlinked}")
    targets = [
        'alfred_mstodo_workflow.py',
        'bin',
        'icon.png',
        'icons',
        'info.plist',
        'logging_setup.py',
        'mstodo',
        'workflow'
    ]
    symlink_items = []
    for target in targets:
        symlink_items.extend(glob.glob(f"{paths.dist_app}/{target}"))
    for item in symlink_items:
        target = os.path.abspath(item)
        dest = paths.tmp_workflow_symlinked + item.removeprefix(paths.dist_app)
        c.run(f"ln -sfhF {target} {dest}")
    return

@task()
def replace(c):
    import re
    import html
    print(" Copying Alfred .plist file and replacing placeholders...")
    metadata = get_metadata_from_pyproject()
    # First escape XML entities for plist (& -> &amp;, < -> &lt;, etc.)
    # Then escape regex special chars for sed, but skip & since it's now &amp;
    changelog_xml = html.escape(open('./changelog.md').read())
    changelog = re.escape(changelog_xml).replace("'", r"\&#39")  # escape ' for shell
    c.run(f"ditto {paths.app}/info.plist {paths.dist_app}")
    with c.cd(paths.dist_app):
        c.run("sed -i '' 's|__changelog__|{}|g' info.plist".format(changelog))
        c.run("""sed -i "" "s|\\&#39|'|g" info.plist""")
        c.run(f"sed -i '' 's#__version__#{metadata['version']}#g' info.plist")
        c.run(f"sed -i '' 's#__title__#{metadata['title']}#g' info.plist")
        c.run(f"sed -i '' 's#__author__#{metadata['author']}#g' info.plist")
        c.run(f"sed -i '' 's#__license__#{metadata['license']}#g' info.plist")
        c.run(f"sed -i '' 's#__copyright__#{metadata['copyright']}#g' info.plist")
        c.run(f"sed -i '' 's#__githubslug__#{metadata['githubslug']}#g' info.plist")
    return

@task(pre=[symlink, replace])
def package_workflow(c, rebuild=False, env=''):
    print(f" Creating Alfred{' ' + env if env else ''} workflow...")
    flag = '-r -FSq' if rebuild else '-rq'
    if env == '':
        # build the workflow by zipping dist/workflow/**/* into /mstodo.alfredworkflow
        with c.cd(paths.dist_app):
            c.run(f"zip -9 {flag} {paths.dist_workflow} .")
            c.run(f"mv {paths.dist_workflow} ../..")
    elif env == "dev":
        # Build dev workflow
        with c.cd(paths.tmp_workflow_symlinked):
            c.run(f"zip --symlinks {flag} {paths.dist_workflow_symlinked} .")
            c.run(f"mv {paths.dist_workflow_symlinked} ../..")
    return

@task
def pylint(c):
    c.run(f"pylint {paths.app} --output-format=json:pylint.json,colorized")
    return

@task
def test(c):
    print(" Running tests...")
    with c.cd(f"{paths.dist_app}"):
        c.run(f"PYTHONPATH=. py.test ../../{paths.tests} --cov-report term-missing --cov mstodo")
    return

@task
def release(c):
    import re
    print(" Creating release")
    metadata = get_metadata_from_pyproject()
    version = metadata['version']
    github_slug = metadata['githubslug']
    title = re.escape(open('./changelog.md').read().splitlines()[0].removeprefix('# '))
    c.run(f"cp ./changelog.md {paths.tmp}/changelog.md")
    with c.cd(paths.tmp):
        c.run(f"sed -i '' '1,2d' changelog.md")
        c.run(f"sed -i '' 's#__version__#{version}#g' changelog.md")
        c.run(f"sed -i '' 's#__githubslug__#{github_slug}#g' changelog.md")

    release_cmd = f"gh release create {version} {paths.dist_workflow} --title {title} --notes-file {paths.tmp}/changelog.md"
    if '-' in version:
        release_cmd = release_cmd + ' --prerelease'
    c.run(release_cmd)