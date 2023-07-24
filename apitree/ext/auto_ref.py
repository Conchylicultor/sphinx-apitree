"""Automatically add cross-links in markdown.

Replace all `my_module.XXX` by `:ref:...` to link to the API doc.

"""
import os
import pathlib
import typing

from docutils import nodes
from sphinx.application import Sphinx

from apitree import context, debug_utils


def _is_inside_link(node: nodes.Node):
    while node.parent:
        if isinstance(node.parent, nodes.reference):
            return True
        node = node.parent
    return False


def _add_refs(app: Sphinx, doctree: nodes.document, docname: str):
    docpath = pathlib.Path(docname + '.md')

    for node in doctree.findall(lambda n: isinstance(n, (nodes.title_reference, nodes.literal))):
        node = typing.cast(nodes.Element, node)

        if _is_inside_link(node):
            continue

        ref_name = node.astext()
        ref_uri = context.get_ref(ref_name.lstrip('@'))

        if ref_uri is None:
            continue

        ref_path = pathlib.Path('api') / ref_uri.match.filename
        ref_path = ref_path.with_suffix('.html')

        ref_path = _relative_path(ref_path, docpath)

        # Wrap inside ref
        ref = nodes.reference(refuri=os.fspath(ref_path))
        ref += nodes.literal(text=ref_name)

        node.replace_self(ref)


def _relative_path(p0: pathlib.Path, p1: pathlib.Path) -> pathlib.Path:
  if p0.is_relative_to(p1):
    return p0.relative_to(p1)

  # Extract the common part between the paths
  num_common_parts = 0
  for part0, part1 in zip(p0.parts, p1.parts):
    if part0 != part1:
      break
    num_common_parts +=1

  num_parents = len(p1.parts) - num_common_parts -1

  new_p = pathlib.Path(*(['..'] * num_parents)).joinpath(*p0.parts[num_common_parts:])
  return new_p



def setup(app: Sphinx):
    app.connect('doctree-resolved', debug_utils.print_error()(_add_refs))
