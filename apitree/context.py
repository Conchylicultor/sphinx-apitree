from __future__ import annotations

import collections
import os
from typing import Optional

from apitree import tree_extractor


class Context:

  def __init__(self):
    self.refs: dict[str, list[tree_extractor.Node]] = collections.defaultdict(list)


def get_ref(name: str) -> Optional[str]:
  matches = _context.refs.get(name)
  if not matches:
    return None
  if len(matches) != 1:
    return None
  return os.fspath(matches[0].match.filename)


def add_ref(node: tree_extractor.Node) -> None:
  name = node.symbol.qualname
  _context.refs[name].append(node)
  if '.' in name:
    _, subname = name.rsplit('.', 1)
    _context.refs[subname].append(node)
  if node.symbol.qualname_no_alias != node.symbol.qualname:
    _context.refs[node.symbol.qualname_no_alias].append(node)



_context = Context()
