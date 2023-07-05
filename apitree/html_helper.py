"""Mini library to help building html code."""

from __future__ import annotations

import functools
from collections.abc import Callable


def tag(name: str, **attributes: str | list[str] | None) -> Callable[..., str]:
  """Create a html tag.

  Usage:

  ```python
  tag('div', id='x')('content') == '<div id="x">content</div>'
  ```

  Args:
    name: Tag name
    **attributes: Attributes of the tag

  Returns:
    The HTML string
  """
  # Could be much more optimized by first building the graph of nested
  # element, then joining individual parts

  attributes = _format_tag_attributes(attributes)

  def apply(*content: str) -> str:
    content = ''.join(content)
    return f'<{name}{attributes}>{content}</{name}>'

  return apply


def _format_tag_attributes(attrs: dict[str, str | list[str]]) -> str:
  """Format the tag attributes."""
  out = ['']
  for k, v in attrs.items():
    if v is None:
      continue
    if k == 'class_':  # `class` is a forbidden Python keyword for arg name
      k = 'class'

    if isinstance(v, str):
      v = v.split()
    elif not isinstance(v, list):
      raise TypeError(f'Unexpected attribute: {k}={v!r}')

    # To avoid collisions, we prefix all classes with `etils-`
    if k == 'class':
      v = [f'etils-{v_}' for v_ in v]

    v = ' '.join(v)

    out.append(f'{k}="{v}"')
  return ' '.join(out)


span = functools.partial(tag, 'span')
ul = functools.partial(tag, 'ul')
li = functools.partial(tag, 'li')
a = functools.partial(tag, 'a')

table = functools.partial(tag, 'table')
thead = functools.partial(tag, 'thead')
tbody = functools.partial(tag, 'table')
tr = functools.partial(tag, 'table')
th = functools.partial(tag, 'table')
