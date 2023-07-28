import functools
import importlib
import inspect
import pathlib
import subprocess

from apitree.context import ctx


@functools.cache
def module_path(module_name: str) -> pathlib.Path:
  """Get absolute path of a module."""
  root_module = importlib.import_module(module_name)
  root_module_path = inspect.getsourcefile(root_module)
  root_module_path = pathlib.Path(root_module_path)
  return root_module_path


# TODO(epot): OO API to allow multiple context with various origins
def repo_path() -> pathlib.Path:
  """Absolute path of the repository."""
  if ctx.curr.path_rel_to_imports:
    # Relative to import
    return abs_path(ctx.curr.module_name.split('.')[0]).parent.parent
  else:
    return _git_repo_path()


@functools.cache
def _git_repo_path():
  out = subprocess.run(
      'git rev-parse --show-toplevel',
      shell=True,
      capture_output=True,
      text=True,
  )
  path = out.stdout.strip()
  return pathlib.Path(path)


@functools.cache
def abs_path(module_name: str) -> pathlib.Path:
  filepath = inspect.getsourcefile(importlib.import_module(module_name))
  if filepath is None:  # E.g. C++ modules
    return None
  filepath = pathlib.Path(filepath)
  return filepath


@functools.cache
def module_lines(module_name: str) -> list[str]:
  filepath = abs_path(module_name)
  return filepath.read_text().split('\n')


def belong_to_repo(module_name: str) -> bool:
  return repo_relative_path(module_name) is not None


@functools.cache
def repo_relative_path(module_name: str) -> pathlib.Path:
  """."""
  filepath = abs_path(module_name)
  if filepath is None:
    return None
  try:
    return filepath.relative_to(repo_path())
  except ValueError:
    return None
