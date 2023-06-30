from __future__ import annotations

import dataclasses
import functools
import pathlib
import types
from collections.abc import Callable
from typing import Any

from etils import edc, epy

from apitree import ast_utils


@edc.dataclass
@dataclasses.dataclass
class Context:
  module_name: str
  # visited: dict[str, _RefNode] = dataclasses.field(default_factory=dict)


@edc.dataclass
@dataclasses.dataclass
class Symbol:
  name: str
  value: Any

  parent: types.ModuleType
  parent_symb: Symbol
  ctx: Context = dataclasses.field(repr=False)

  @functools.cached_property
  def is_imported(self) -> bool:
    return self.name in self.imported_symbols

  @functools.cached_property
  def imported_symbols(self) -> set[str]:
    if self.parent.__file__ is None:  # Implicit package
      return set()
    # TODO(epot): Cache across module
    return set(imp.alias for imp in ast_utils.parse_global_imports(self.parent))

  @functools.cached_property
  def is_package(self) -> bool:
    # TODO(epot): Could also add custom attribute `__docutil__.is_package` so
    # standard module behave like package.
    return _is_package(self.value)

  @functools.cached_property
  def belong_to_namespace(self) -> bool:
    return self.value.__name__.startswith(self.ctx.module_name)

  @functools.cached_property
  def match(self) -> type[Match]:
    return Match.root_match(self)

  # Return type


class Match:
  symbol: Symbol

  recurse: bool = False
  documented = True

  SUBCLASSES: list[Match] = []

  def __init__(self, symbol):
    self.symbol = symbol

  def __init_subclass__(cls) -> None:
    if 'SUBCLASSES' not in cls.__dict__:
      cls.SUBCLASSES = []
    for parent_cls in cls.__bases__:
      parent_cls.SUBCLASSES.append(cls)

  @classmethod
  def root_match(cls, symbol: Symbol) -> Match:
    for subcls in cls.SUBCLASSES:
      all_match = []
      self = subcls(symbol)
      for subcls_parents in subcls.mro():
        if subcls_parents is object:
          continue
        try:
          all_match.append(subcls_parents.match(self))
        except Exception as e:
          epy.reraise(
              e, prefix=f'{symbol} ({cls.__name__}) for {subcls.__name__}'
          )

      if all(all_match):  # Found match
        return subcls.root_match(symbol)  # Maybe missing values, recurse
    else:
      if not cls.SUBCLASSES:  # Leaf
        return cls(symbol)
      raise ValueError(f'No match found for {symbol} (in {cls})')

  def match(cls) -> bool:
    return True

  # Write the doc

  @property
  def filename(self) -> pathlib.Path:
    raise ValueError(f'Missing filename for {type(self)}')


def _not(cls: type[Match]) -> Callable[[Match], bool]:
  def match(self):
    return not cls.match(self)

  return match


class _IsModule(Match):

  def match(self) -> bool:
    return isinstance(self.symbol.value, types.ModuleType)

  @property
  def filename(self) -> pathlib.Path:
    return (
        self.symbol.parent_symb.match.filename.parent
        / self.symbol.name
        / 'index.rst'
    )


class _RootModule(_IsModule):
  recurse = True

  def match(self) -> bool:
    return self.symbol.parent is None

  @property
  def filename(self) -> pathlib.Path:
    return pathlib.Path(self.symbol.name) / 'index.rst'


class _ImplicitlyImportedModule(_IsModule):
  """Filter implicitly imported modules."""

  documented = False

  def match(self) -> bool:
    return not self.symbol.is_imported


class _ExternalModule(_IsModule):
  documented = False

  def match(self) -> bool:
    return not self.symbol.belong_to_namespace


class _BelongToNamespace(_IsModule):

  def match(self) -> bool:
    return self.symbol.belong_to_namespace


class _IsPackage(_IsModule):

  def match(self) -> bool:
    return self.symbol.is_package


class _ApiPackage(_BelongToNamespace, _IsPackage):
  recurse = True


class _ApiModule(_BelongToNamespace, _IsModule):

  @property
  def documented(self):
    # Only document when the parent is a package
    return _is_package(self.symbol.parent)

  @property
  def recurse(self):
    # Only recurse when the parent is a package
    return _is_package(self.symbol.parent)


class _IsValue(Match):
  match = _not(_IsModule)

  @property
  def filename(self) -> pathlib.Path:
    return (
        self.symbol.parent_symb.match.filename.parent
        / f'{self.symbol.name}.rst'
    )


class _PrivateValue(_IsValue):
  documented = False

  def match(self) -> bool:
    return self.symbol.name.startswith('_')


class _MagicModuleAttribute(_IsValue):
  documented = False

  def match(self):
    return self.symbol.name in [
        '__name__',
        '__doc__',
        '__package__',
        '__loader__',
        '__spec__',
        '__path__',
        '__file__',
        '__cached__',
        '__builtins__',
    ]


class _FutureAnnotation(_IsValue):
  documented = False

  def match(self):
    import __future__

    return isinstance(self.symbol.value, __future__._Feature)


class _ImportedValue(_IsValue):

  @property
  def documented(self):
    # Only document imported values when the parent is a package
    return _is_package(self.symbol.parent)

  def match(self):
    return self.symbol.is_imported


class _DocumentedValue(_IsValue):
  pass


def _is_package(module: types.ModuleType) -> bool:
  # TODO(epot): Could also add custom attribute `__docutil__.is_package` so
  # standard module behave like package.
  return module.__name__ == module.__package__
  # return pathlib.Path(module.__file__).name == '__init__.py'
