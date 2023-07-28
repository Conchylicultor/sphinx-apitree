from __future__ import annotations

import collections
import os
from typing import Optional

from apitree import structs, tree_extractor


class Context:

  def __init__(self):
    self.refs: dict[str, list[tree_extractor.Node]] = collections.defaultdict(
        list
    )
    self.curr: structs.ModuleInfo = None


def get_ref(name: str) -> Optional[tree_extractor.Node]:
  matches = ctx.refs.get(name)
  if not matches:
    return None
  if len(matches) != 1:
    return None
  return matches[0]


def add_ref(node: tree_extractor.Node) -> None:
  name = node.symbol.qualname
  ctx.refs[name].append(node)
  if '.' in name:
    _, subname = name.rsplit('.', 1)
    ctx.refs[subname].append(node)
  # `qualname_no_alias` is acually the real module name.
  # Could also add the real `qualname_no_alias`. For example:
  # * `kd.typing.XX`  # Public symbol
  # * `kauldron.typing.XX`  # Alias replaced
  # * `kauldron.utils.typing.XX`  # Real module location
  if node.symbol.qualname_no_alias != node.symbol.qualname:
    ctx.refs[node.symbol.qualname_no_alias].append(node)


ctx = Context()
