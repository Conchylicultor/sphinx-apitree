import os
import types

from etils import epath, epy

from apitree import md_utils, symbol_match, tree_extractor


def write_doc(node: tree_extractor.Node | types.ModuleType) -> None:
  if not isinstance(node, tree_extractor.Node):
    node = tree_extractor.get_api_tree(node)

  root_dir = epath.resource_path(node.symbol.value)
  root_dir = root_dir.parent / 'docs/api'

  # import apitree
  # root_dir = epath.Path(apitree.__file__).parent.parent
  # root_dir = root_dir / '_build'

  if root_dir.exists():
    root_dir.rmtree()
  root_dir.mkdir(exist_ok=True)

  _write_all_symbols(root_dir, node)

  _write_node(root_dir, node)


def _write_all_symbols(root_dir: epath.Path, node: tree_extractor.Node) -> None:
  table = md_utils.Table(header=['', '', ''])

  for n in node.iter_documented_nodes():
    filename = n.match.filename
    filename = os.fspath(filename)
    filename = filename.removesuffix('.md')
    table.add_row(
        f'*{n.match.icon}*',
        f'[{n.symbol.qualname}]({filename})',
        f'{n.match.docstring_1line}',
    )

  content = symbol_match.load_template('api').format(symbols=table.make())

  f = root_dir / '_api.md'
  f.write_text(content)


def _write_node(root_dir: epath.Path, node: tree_extractor.Node) -> None:
  file = root_dir / node.match.filename
  file.parent.mkdir(exist_ok=True, parents=True)
  file.write_text(epy.dedent(node.match.content))

  for child in node.childs:
    if not child.match.documented:
      continue
    _write_node(root_dir, child)
