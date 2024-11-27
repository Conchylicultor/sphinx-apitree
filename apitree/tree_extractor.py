from __future__ import annotations

import dataclasses
import functools
import importlib
import types
from typing import Iterator

from etils import edc, epy

from apitree import context, structs, symbol_match


@dataclasses.dataclass
class Node:
  symbol: symbol_match.Symbol

  def __post_init__(self):
    self.symbol.node = self
    context.add_ref(self)

  @property
  def match(self):
    return self.symbol.match

  @functools.cached_property
  def childs(self) -> list[Node]:
    if not self.match.recurse:
      return []
    module = self.symbol.value
    all_childs = []
    # Iterate with `dir` to resolve `epy.lazy_api_imports`
    for k in dir(module):
      v = getattr(module, k)
      symbol = symbol_match.Symbol(
          name=k,
          value=v,
          parent=module,
          parent_symb=self,
          ctx=self.symbol.ctx,
      )
      all_childs.append(Node(symbol))

    return all_childs

  @functools.cached_property
  def documented_childs(self) -> list[Node]:
    return [n for n in self.childs if n.match.documented]

  def iter_documented_nodes(self) -> Iterator[Node]:
    yield self
    for c in self.documented_childs:
      yield from c.iter_documented_nodes()

  def __repr__(self) -> str:
    if self.childs:
      if hasattr(epy, 'pretty_repr'):
        pretty_fn = epy.pretty_repr
      else:
        pretty_fn = epy.Lines.repr
      child_str = pretty_fn([c for c in self.childs if c.match.documented])
    else:
      child_str = ''
    return f'{self.symbol.name}={type(self.match).__name__}{child_str}'


def get_api_tree(info: structs.ModuleInfo):
  module = importlib.import_module(info.api)

  # ctx = symbol_match.Context(
  #     module_name=module.__name__,
  #     info,
  # )
  return Node(
      symbol_match.Symbol(
          name=module.__name__,
          value=module,
          parent=None,
          parent_symb=None,
          ctx=info,
      ),
  )
