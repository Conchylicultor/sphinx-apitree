from __future__ import annotations

import dataclasses
import functools
import os
import pathlib
import types
from collections.abc import Callable, Iterator
from typing import Any

import typing_extensions
from etils import edc, epath, epy

from apitree import ast_utils, md_utils, tree_extractor


@edc.dataclass
@dataclasses.dataclass
class Context:
  module_name: str
  alias: str
  # visited: dict[str, _RefNode] = dataclasses.field(default_factory=dict)


@edc.dataclass
@dataclasses.dataclass
class Symbol:
  name: str
  value: Any

  parent: types.ModuleType
  parent_symb: tree_extractor.Node
  ctx: Context = dataclasses.field(repr=False)

  node: tree_extractor.Node = dataclasses.field(repr=False, init=False)

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
  def belong_to_namespace(self) -> bool:
    return self.value.__name__.startswith(self.ctx.module_name)

  @functools.cached_property
  def match(self) -> type[Match]:
    return Match.root_match(self)

  @functools.cached_property
  def qualname(self) -> bool:
    """Exemple: `dca.typing.Float`."""
    if self.parent_symb is None:  # root node
      # assert self.ctx.module_name == self.name
      return self.ctx.alias
    return f'{self.parent_symb.symbol.qualname}.{self.name}'

  @functools.cached_property
  def qualname_no_alias(self) -> bool:
    """Exemple: `dataclass_array.typing.Float`."""
    if self.parent_symb is None:  # root node
      return self.name
    return f'{self.parent_symb.symbol.qualname_no_alias}.{self.name}'

  # Return type


class Match:
  symbol: Symbol

  recurse: bool = False
  documented = True
  template_name: str | None = None
  docstring_1line: str = ''
  icon: str = ''

  extra_template_kwargs = {}

  SUBCLASSES: list[Match] = []
  SKIP_REGISTRATION = False

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
      if subcls.__dict__.get('SKIP_REGISTRATION', False):
        continue
      all_match = []
      self = subcls(symbol)
      for subcls_parents in subcls.mro():
        if subcls_parents is object:
          continue
        if subcls_parents.__dict__.get('SKIP_REGISTRATION', False):
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

  @functools.cached_property
  def template(self) -> str:
    if not self.template_name:
      return ''
    return load_template(self.template_name)

  @property
  def content(self):
    # TODO(epot)
    # * Title
    # * Docstring
    # * Signature
    # * Arguments
    # * Source code
    return self.template.format(
        qualname=self.symbol.qualname,
        qualname_no_alias=self.symbol.qualname_no_alias,
        **self.extra_template_kwargs,
    )

  def make_symbols_table(self, nodes: Iterator[tree_extractor.Node]):
    table = md_utils.Table(header=['', '', ''])

    for n in nodes:
      filename = n.match.filename
      filename = filename.relative_to(self.filename.parent)
      filename = os.fspath(filename)
      filename = filename.removesuffix('.md')
      table.add_row(
          f'*{n.match.icon}*',
          f'[{n.symbol.qualname}]({filename})',
          f'{n.match.docstring_1line}',
      )

    return table.make()


def _not(cls: type[Match]) -> Callable[[Match], bool]:
  def match(self):
    return not cls.match(self)

  return match


@functools.cache
def load_template(template_name):
  path = epath.resource_path('apitree') / f'templates/{template_name}.md'
  return path.read_text()


class _WithDocstring(Match):
  SKIP_REGISTRATION = True

  @property
  def docstring_1line(self) -> str:
    if not getattr(self.symbol.value, '__doc__', None):
      return ''
    else:
      return self.symbol.value.__doc__.split('\n', 1)[0]


class _IsModule(_WithDocstring, Match):
  icon = 'm'
  template_name = 'module'

  def match(self) -> bool:
    return isinstance(self.symbol.value, types.ModuleType)

  @property
  def filename(self) -> pathlib.Path:
    return (
        self.symbol.parent_symb.match.filename.parent
        / self.symbol.name
        / 'index.md'
    )

  @property
  def extra_template_kwargs(self):
    return dict(
        toctree=self.toctree,
        symbols_table=self.make_symbols_table(
            self.symbol.node.documented_childs
        ),
    )

  @property
  def toctree(self) -> str:
    items = []
    for n in self.symbol.node.documented_childs:
      path = n.match.filename.relative_to(self.filename.parent)
      path = os.fspath(path)
      path = path.removesuffix('.md')
      items.append(path)
    return '\n'.join(items)


class _RootModule(_IsModule):
  recurse = True
  template_name = 'api'

  def match(self) -> bool:
    return self.symbol.parent is None

  @property
  def filename(self) -> pathlib.Path:
    # return pathlib.Path(self.symbol.name) / 'index.md'
    return pathlib.Path(self.symbol.ctx.alias) / 'index.md'

  @property
  def extra_template_kwargs(self):
    return dict(
        **super().extra_template_kwargs,
        import_statement=self.import_statement,
        all_symbols_table=self.make_symbols_table(
            self.symbol.node.iter_documented_nodes()
        ),
    )

  @property
  def import_statement(self) -> str:
    module_name = self.symbol.ctx.module_name
    alias = self.symbol.ctx.alias

    if '.' in module_name:
      left, last_name = module_name.rsplit('.')
      left = f'from {left} '
    else:
      left = ''
      last_name = module_name

    if last_name == alias:
      stmt = f'import {last_name}'
    else:
      stmt = f'import {last_name} as {alias}'

    stmt = left + stmt
    return epy.dedent(
        f"""
        ```{{code-block}}
        {stmt}
        ```
        """
    )


class _ImplicitlyImportedModule(_IsModule):
  """Filter implicitly imported modules."""

  documented = False

  def match(self) -> bool:
    return not self.symbol.is_imported


class _ExternalModule(_IsModule):
  documented = False

  def match(self) -> bool:
    return not self.symbol.belong_to_namespace


class _ApiModule(_IsModule):
  """Modules or packages."""

  def match(self) -> bool:
    return self.symbol.belong_to_namespace

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
        self.symbol.parent_symb.match.filename.parent / f'{self.symbol.name}.md'
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


class _DocumentedValue(_IsValue):

  @property
  def documented(self):
    # Only document imported values when the parent is a package
    return not self.symbol.is_imported or _is_package(self.symbol.parent)


# TODO(epot): How to duplicate this with _ImportedValue ?


class _TypeAliasValue(_DocumentedValue):
  icon = 't'
  template_name = 'type_alias'

  def match(self):
    # TODO(epot): How to detect `Any`,...
    return typing_extensions.get_origin(self.symbol.value) is not None


class _ClassValue(_WithDocstring, _DocumentedValue):
  icon = 'c'
  template_name = 'class'

  def match(self):
    return isinstance(self.symbol.value, type)


class _FunctionValue(_WithDocstring, _DocumentedValue):
  icon = 'f'
  template_name = 'function'

  def match(self):
    return isinstance(
        self.symbol.value, (types.FunctionType, functools.partial)
    )


class _AttributeValue(_DocumentedValue):
  icon = 'a'
  template_name = 'attribute'

  # TODO(epot): Extract doc from parent


def _is_package(module: types.ModuleType) -> bool:
  # Have custom attribute so standard module can behave like package.
  if hasattr(module, '__apitree__'):
    return module.__apitree__['is_package']
  return module.__name__ == module.__package__
