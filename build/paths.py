# Directory names
# for consistent directories across app, .tmp, www, and dist
app_dirname = "src"
bin_dirname = "bin"
lib_dirname = "lib"
dist_dirname = "dist"
icons_dirname = "icons"

# Source code
app = app_dirname
app_bin = app + "/" + bin_dirname
app_lib = lib_dirname
app_module = app + "/mstodo"
app_icons = app + "/" + icons_dirname

tests = "tests"

# Built distribution
dist = dist_dirname

dist_app = dist + "/workflow"
dist_bin = dist_app + "/" + bin_dirname
dist_lib = dist_app
dist_icons = dist_app + "/" + icons_dirname

# Final binaries, make them easy to find in the repo root
dist_workflow = "mstodo.alfredworkflow"
dist_workflow_symlinked = "mstodo-symlinked.alfredworkflow"

# Temporary paths
tmp = ".tmp"
tmp_img = tmp + "/" + icons_dirname
tmp_workflow_symlinked = tmp + "/workflow-symlinked"