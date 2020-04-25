
Helpers for running pylint with py.test and have configurable rule
types (i.e. Convention, Warn, and Error) fail the
build. You can also specify a pylintrc file.

How it works

We have a thin plugin wrapper that is installed through setup.py hooks as `pylint`.
This wrapper uses pytest_addoption and pytest_configure to decide to configure and
register the real plugin PylintPlygin

Once it is registered in `pytest_configure`, the hooks already executed
by previous plugins will run. For instance, in case PylintPlugin had
`pytest_addoption` implemented, which runs before `pytest_configure`
in the hook cycle, it would be executed once PylintPlugin got registered.

PylintPlugin uses the `pytest_collect_file` hook which is called wih every
file available in the test target dir. This hook collects all the file
pylint should run on, in this case files with extension ".py".

`pytest_collect_file` hook returns a collection of Node, or None. In
py.test context, Node being a base class that defines py.test Collection
Tree.

A Node can be a subclass of Collector, which has children, or an Item, which
is a leaf node.

A practical example would be, a Python test file (Collector), can have multiple
test functions (multiple Items)

For this plugin, the relatioship of File to Item is one to one, one
file represents one pylint result.

From that, there are two important classes: PyLintFile, and PyLintItem.

PyLintFile represents a python file, extension ".py", that was
collected based on target directory as mentioned previously.

PyLintItem represents one file which pylint was ran or will run.

Back to PylintPlugin, `pytest_collection_finish` hook will run after the
collection phase where pylint will be ran on the collected files.

Based on the ProgrammaticReporter, the result is stored in a dictionary
with the file relative path of the file being the key, and a list of
errors related to the file.

All PylintFile returned during `pytest_collect_file`, returns an one
element list of PyLintItem. The Item implements runtest method which will
get the pylint messages per file and expose to the user.
