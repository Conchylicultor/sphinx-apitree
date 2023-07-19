"""Add links to GitHub source code."""

import functools
import importlib
import inspect
import pathlib
import subprocess

from apitree import ast_utils


def linkcode_resolve(domain, info):
  if domain != 'py':
    return None
  if not info['module']:
    return None

  # filepath = _get_filepath(info['module'])
  filepath = _get_lines_suffix(info['module'], info['fullname'])
  if not filepath:
    if '.' in info['fullname']:
      # Attributes are not documented (as they beloong to different files)
      return None
    # Fallback on the module name.
    # TODO(epot): Should point where the object is created
    filepath = _get_definition_line(info['module'], info['fullname'])
  return f'{_get_github_url()}/tree/main/{filepath}'


def _get_definition_line(module_name, qualname):
  filename = _rel_filepath(module_name, _module_path(module_name))

  # Parse ast to find the line number
  assignements = _get_symbols(module_name)

  if qualname in assignements:
    return f'{filename}#L{assignements[qualname]}'
  else:
    return filename


def _get_lines_suffix(module_name: str, qualname: str) -> str:
  module = importlib.import_module(module_name)

  obj = module
  for part in qualname.split('.'):
    try:
      obj = getattr(obj, part)
    except AttributeError:
      return ''  # Object unavailable

  obj = inspect.unwrap(obj)

  try:
    filepath = inspect.getsourcefile(obj)
  except TypeError:
    return ''

  try:
    lines = inspect.getsourcelines(obj)
  except (TypeError, OSError):
    return ''

  # Detect if file is inside the project (and not `Union` or similar)
  filepath = _rel_filepath(module_name, filepath)
  if not filepath:
    return ''

  start = lines[1]
  end = start + len(lines[0]) - 1
  return f'{filepath}#L{start}-L{end}'


def _rel_filepath(module_name, filepath):
  root_dir = _root_path(module_name)
  filepath = pathlib.Path(filepath)
  try:
    return filepath.relative_to(root_dir)
  except ValueError:
    return None


@functools.cache
def _module_path(module_name) -> pathlib.Path:
  root_module = importlib.import_module(module_name)
  root_module_path = inspect.getsourcefile(root_module)
  root_module_path = pathlib.Path(root_module_path)
  return root_module_path


@functools.cache
def _get_symbols(module_name) -> dict[str, int]:
  path = _module_path(module_name)
  return ast_utils.extract_assignement_lines(path.read_text())


def _root_path(module_name) -> pathlib.Path:
  module_name = module_name.split('.', 1)[0]
  return _module_path(module_name).parent.parent


@functools.cache
def _get_github_url() -> str:
  # TODO(epot): Support cross-repo
  out = subprocess.run(
      'git config --get remote.origin.url',
      shell=True,
      capture_output=True,
      text=True,
  )
  url = out.stdout.strip()
  assert url.startswith('https://github.com')
  return url


# Could try to use `app.builder.env` to auto-setup the extension
