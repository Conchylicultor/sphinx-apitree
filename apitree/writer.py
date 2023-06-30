from etils import epath

from apitree import tree_extractor


def write_doc(node: tree_extractor.Node) -> None:
  import apitree

  root_dir = epath.Path(apitree.__file__).parent.parent
  root_dir = root_dir / '_build'

  root_dir.rmtree()
  root_dir.mkdir(exist_ok=True)

  _write_node(root_dir, node)


def _write_node(root_dir: epath.Path, node: tree_extractor.Node) -> None:
  file = root_dir / node.match.filename
  file.parent.mkdir(exist_ok=True, parents=True)
  file.write_text('')

  for child in node.childs:
    if not child.match.documented:
      continue
    _write_node(root_dir, child)


import visu3d

tree = tree_extractor.get_api_tree(visu3d)
write_doc(tree)
print(tree)

import etils
from etils import enp, epy

print(tree_extractor.get_api_tree(epy))
print(tree_extractor.get_api_tree(enp))
