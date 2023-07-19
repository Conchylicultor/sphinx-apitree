"""Automatically add cross-links in markdown.

Replace all `my_module.XXX` by `:ref:...` to link to the API doc.

"""
import typing

from docutils import nodes
from sphinx.application import Sphinx

from apitree import context


def _is_inside_link(node: nodes.Node):
    while node.parent:
        if isinstance(node.parent, nodes.reference):
            return True
        node = node.parent
    return False


def _add_refs(app: Sphinx, doctree: nodes.document, docname: str):
    for node in doctree.findall(nodes.literal):
        node = typing.cast(nodes.Element, node)

        if _is_inside_link(node):
            continue

        ref_name = node.astext()
        ref_uri = context.get_ref(ref_name.lstrip('@'))

        if ref_uri is None:
            continue

        # Wrap inside ref
        ref = nodes.reference(refuri=ref_uri)
        ref += nodes.literal(text=ref_name)

        node.replace_self(ref)


def setup(app: Sphinx):
    app.connect('doctree-resolved', _add_refs)
