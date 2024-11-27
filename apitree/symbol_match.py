from __future__ import annotations

import dataclasses
import enum
import functools
import inspect
import os
import pathlib
import sys
import types
import typing
from collections.abc import Callable, Iterator
from typing import Any

import typing_extensions
from etils import edc, epath, epy

from apitree import ast_utils, context, md_utils, tree_extractor
from apitree.ext import github_link


@edc.dataclass
@dataclasses.dataclass
class Context:
  module_name: str
  alias: str
  # visited: dict[str, _RefNode] = dataclasses.field(default_factory=dict)


class SymbolType(enum.StrEnum):
  MODULE = enum.auto()
  CLASS = enum.auto()
  FUNCTION = enum.auto()
  ATTRIBUTE = enum.auto()
  TYPING = enum.auto()
  UNKNOWN = enum.auto()


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
  def qualname(self) -> str:
    """Exemple: `dca.typing.Float`."""
    if self.parent_symb is None:  # root node
      # assert self.ctx.module_name == self.name
      return self.ctx.alias
    return f'{self.parent_symb.symbol.qualname}.{self.name}'

  @functools.cached_property
  def qualname_no_alias(self) -> str:
    """Exemple: `dataclass_array.typing.Float`."""
    if isinstance(self.value, types.ModuleType):
      try:
        return self.value.__name__
      except Exception:  # TODO(epot): Better lazy-modules
        return ''
    else:
      return f'{self.parent_symb.symbol.qualname_no_alias}.{self.name}'

  # Return type


class Match:
  symbol: Symbol

  recurse: bool = False
  documented = True
  template_name: str | None = None
  docstring_1line: str = ''
  icon: SymbolType = SymbolType.UNKNOWN

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
    table = md_utils.Table(header=['', ''])

    for n in nodes:
      filename = n.match.filename
      filename = filename.relative_to(self.filename.parent)
      filename = os.fspath(filename)
      filename = filename.removesuffix('.md')
      table.add_row(
          # f'*{n.match.icon}*',
          f'[{n.symbol.qualname}]({filename})',
          f'{n.match.docstring_1line}',
      )

    return table.make()

  def make_symbols_tables(self, nodes: tree_extractor.Node) -> str:
    type_to_childs = epy.groupby(nodes, key=lambda n: n.match.icon)
    lines = []
    for type_ in SymbolType:
      if type_ not in type_to_childs:
        continue
      lines.append('')
      lines.append(f'### {type_.capitalize()}')
      lines.append('')

      childs = type_to_childs[type_]
      childs = sorted(childs, key=lambda n: n.symbol.qualname)
      lines.append(self.make_symbols_table(childs))
    return '\n'.join(lines)


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
  icon = SymbolType.MODULE
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
        symbols_table=self.make_symbols_tables(
            self.symbol.node.documented_childs
        ),
        source_link=github_link.get_module_link(self.symbol.value.__name__),
        **super().extra_template_kwargs,
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
        all_symbols_table=self.make_symbols_tables(
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


class _WithSourceLink(Match):

  @functools.cached_property
  def _ast_symbol(self):
    module_name = self.symbol.parent.__name__
    name = self.symbol.name

    return ast_utils.extract_last_symbol(module_name, name)

  @property
  def docstring_1line(self) -> str:
    doc = ' '.join(self._ast_symbol.docstring.split('\n'))
    if len(doc) > 83:  # Truncate
      return doc[:80] + '...'
    else:
      return doc

  @property
  def extra_template_kwargs(self):
    module_name = self.symbol.parent.__name__
    name = self.symbol.name

    source_link = github_link.get_assignement_link(module_name, name)

    return dict(
        source_link=source_link,
        source_code=self._ast_symbol.code,
        docstring=self._ast_symbol.docstring,
        **super().extra_template_kwargs,
    )


class _TypeAliasValue(_DocumentedValue, _WithSourceLink):
  icon = SymbolType.TYPING
  template_name = 'type_alias'

  def match(self):
    # TODO(epot): How to detect `Any`,...

    return (
        isinstance(self.symbol.value, typing.TypeVar)
        or typing_extensions.get_origin(self.symbol.value) is not None
    )


class _ClassValue(_WithDocstring, _DocumentedValue):
  icon = SymbolType.CLASS
  template_name = 'class'

  def match(self):
    return isinstance(self.symbol.value, type)


class _FunctionValue(_WithDocstring, _DocumentedValue):
  icon = SymbolType.FUNCTION
  template_name = 'function'

  def match(self):
    # Unwrap to support class decorator like:
    # * `@functools.cache`
    # * `@jax.jit`
    # TODO(epot): Could move static_unwrap to `epy` ?
    obj = _static_unwrap(self.symbol.value)
    return isinstance(
        obj,
        (
            types.FunctionType,
            types.BuiltinFunctionType,
            types.BuiltinMethodType,
            types.MethodType,
            types.MethodWrapperType,
        ),
    )


class _AttributeValue(_DocumentedValue, _WithSourceLink):
  icon = SymbolType.ATTRIBUTE
  template_name = 'attribute'


def _is_package(module: types.ModuleType) -> bool:
  # Have custom attribute so standard module can behave like package.
  if hasattr(module, '__apitree__'):
    return module.__apitree__['is_package']
  if module.__name__ in context.ctx.curr.should_be_packages:
    return True
  return module.__name__ == module.__package__


def _static_unwrap(func):
  """Like `inspect.unwrap`, but do not trigger `__getattr__`."""
  f = func  # remember the original func for error reporting
  # Memoise by id to tolerate non-hashable objects, but store objects to
  # ensure they aren't destroyed, which would allow their IDs to be reused.
  memo = {id(f): f}
  recursion_limit = sys.getrecursionlimit()
  while not isinstance(func, type) and inspect.getattr_static(
      func, '__wrapped__', None
  ):
    func = func.__wrapped__
    id_func = id(func)
    if (id_func in memo) or (len(memo) >= recursion_limit):
      raise ValueError('wrapper loop when unwrapping {!r}'.format(f))
    memo[id_func] = func
  return func
