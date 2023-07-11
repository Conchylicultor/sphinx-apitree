import os
import types

from etils import epath, epy

from apitree import structs, symbol_match, tree_extractor


def write_doc(
    info: structs.ModuleInfo,
    *,
    verbose=True,
    module_info: structs.ModuleInfo = None,
    root_dir: epath.Path = None,
) -> None:
  node = tree_extractor.get_api_tree(info)
  if not root_dir:
    root_dir = epath.resource_path(node.symbol.value)
    root_dir = root_dir.parent / 'docs/api'

  if verbose:
    print(node)

  _write_node(root_dir, node)


def _write_node(root_dir: epath.Path, node: tree_extractor.Node) -> None:
  file = root_dir / node.match.filename
  file.parent.mkdir(exist_ok=True, parents=True)
  file.write_text(epy.dedent(node.match.content))

  for child in node.documented_childs:
    _write_node(root_dir, child)
