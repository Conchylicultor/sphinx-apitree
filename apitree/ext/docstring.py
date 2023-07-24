"""Fix bad ```python md formatting."""

from sphinx.application import Sphinx

from apitree import debug_utils


def _preprocess_docstring(app, what, name, obj, options, lines):
  # Modify each line of the docstring
  is_block = False
  new_lines = []
  for line in lines:
    if line == '```python':
      assert not is_block
      new_lines.append('.. code-block::')
      new_lines.append('')
      is_block = True
    elif line == '```':
      if is_block:
        new_lines.append('')
      else:
        new_lines.append('.. code-block::')
        new_lines.append('')
      is_block = not is_block
    else:
      if is_block:
        line = f'  {line}'
      new_lines.append(line)
  lines[:] = new_lines


def setup(app: Sphinx):
  # Fix bad ```python md formatting
  app.connect(
      'autodoc-process-docstring',
      debug_utils.print_error()(_preprocess_docstring),
  )
