"""Add links to GitHub source code."""

import functools
import importlib
import inspect
import pathlib
import subprocess

from apitree import ast_utils, debug_utils, import_utils


@debug_utils.print_error()
def linkcode_resolve(domain, info):
  if domain != 'py':
    return None
  if not info['module']:
    return None
  return _linkcode_resolve(info['module'], info['fullname'])


def _linkcode_resolve(module_name: str, fullname: str) -> str:
  suffix = _get_lines_suffix(module_name, fullname)
  if not suffix:
    if '.' in fullname:
      # Attributes are not documented (as they beloong to different files)
      return None
    # Fallback on the module name.
    symbol = ast_utils.extract_last_symbol(module_name, fullname)
    if symbol is None:
      raise ValueError(f"{module_name}:{fullname} not found.")
    suffix = f'{symbol.filename}{symbol.git_lno}'
  return f'{_get_github_url()}/tree/main/{suffix}'


def get_module_link(module_name):
  path = import_utils.repo_relative_path(module_name)
  return f'{_get_github_url()}/tree/main/{path}'


def get_assignement_link(module_name, name):
  symbol = ast_utils.extract_last_symbol(module_name, name)
  if symbol is None:
    raise ValueError(f'{module_name}:{name} not found.')

  source_link = (
      f'{_get_github_url()}/tree/main/{symbol.filename}{symbol.git_lno}'
  )
  return source_link


def _get_lines_suffix(module_name: str, qualname: str) -> str:
  module = importlib.import_module(module_name)

  obj = module
  for part in qualname.split('.'):
    try:
      obj = getattr(obj, part)
    except AttributeError:
      return ''  # Object unavailable

  obj = inspect.unwrap(obj)

  # After unwrapping, the object might be in a different file
  try:
    _module = inspect.getmodule(obj)
    if _module is None:  # Class attributes (e.g. `x: int`)
      return ''
      # raise ValueError(f'Not found: {module_name} {qualname}')
    module_name = _module.__name__
  except TypeError:
    return ''

  try:
    lines = inspect.getsourcelines(obj)
  except (TypeError, OSError):
    return ''

  # Detect if file is inside the project (and not `Union` or similar)
  filepath = import_utils.repo_relative_path(module_name)
  if not filepath:
    return ''

  start = lines[1]
  end = start + len(lines[0]) - 1
  return f'{filepath}#L{start}-L{end}'


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
