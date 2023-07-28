from __future__ import annotations

import ast
import contextlib
import dataclasses
import functools
import inspect
import os
import types

from etils import epy

from apitree import import_utils


@dataclasses.dataclass
class ImportAlias:
  """Represents an import symbol."""

  namespace: str
  alias: str


class _GlobalImportVisitor(ast.NodeVisitor):

  def __init__(self):
    self.symbols = []

  def visit_Import(self, node):
    for alias in node.names:
      self.symbols.append(
          ImportAlias(alias.name, alias.asname or alias.name.split('.', 1)[0])
      )
    self.generic_visit(node)

  def visit_ImportFrom(self, node):
    module = node.module or ''
    for alias in node.names:
      self.symbols.append(
          ImportAlias(f'{module}.{alias.name}', alias.asname or alias.name)
      )
    self.generic_visit(node)

  def generic_visit(self, node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
      return
    return super().generic_visit(node)


def parse_global_imports(content: str | types.ModuleType) -> list[ImportAlias]:
  """Extracts import symbols from a Python module.

  Args:
    module: The Python module to extract import symbols from.

  Returns:
    A list of Symbol objects representing the import symbols.

  """
  if isinstance(content, types.ModuleType):
    content = inspect.getsource(content)
  tree = ast.parse(content)

  visitor = _GlobalImportVisitor()
  visitor.visit(tree)

  return visitor.symbols


@dataclasses.dataclass
class _SymbolDefinition:
  module_name: str
  start: int
  end: int

  @property
  def git_lno(self) -> str:
    if self.start == self.end:
      return f'#L{self.start}'
    else:
      return f'#L{self.start}-L{self.end}'

  @property
  def belong_to_project(self) -> bool:
    return import_utils.belong_to_repo(self.module_name)

  @property
  def filename(self) -> str:
    return os.fspath(import_utils.repo_relative_path(self.module_name))

  @property
  def last_project_symbol(self) -> _SymbolDefinition:
    if not self.belong_to_project:
      raise ValueError(
          f'{self.module_name} is not part of the project.\n'
          f' * Repo: {import_utils.repo_path()}\n'
          f' * Proj: {import_utils.abs_path(self.module_name)}\n'
          'Make sure that the project was installed locally (`pip install'
          ' -e .`)'
      )
    return self

  @property
  def docstring(self) -> str:
    # TODO(epot): Should also support `Attributes:` docstring
    # What if the `Attributes:` is hidden in the import chain ?
    lines = import_utils.module_lines(self.module_name)
    docstring_lines = []
    for lines_no in range(self.start - 2, 0, -1):
      line = lines[lines_no].strip()
      if not line.startswith('# '):
        break
      line = line.removeprefix('# ')
      docstring_lines.append(line)
    return '\n'.join(reversed(docstring_lines))

  @property
  def code(self) -> str:
    lines = import_utils.module_lines(self.module_name)
    lines = lines[self.start - 1 : self.end]
    return '\n'.join(lines)


@dataclasses.dataclass
class _ImportedSymbol(_SymbolDefinition):
  import_module_name: str
  symbol_name: str

  @property
  def last_project_symbol(self) -> _SymbolDefinition:
    if not self.belong_to_project:
      raise ValueError(f'{self.module_name} is not part of the project.')

    # No need to load the child if it do not belong to the module
    if import_utils.repo_relative_path(self.import_module_name) is None:
      return self

    sub_symbols = extract_symbols(self.import_module_name)
    if self.symbol_name not in sub_symbols:
      raise ValueError(
          f'`{self.symbol_name}` not found in `{self.import_module_name}`'
      )
    sub = sub_symbols[self.symbol_name]
    if not sub.belong_to_project:  # The child do not bellong to the project
      return self

    return sub.last_project_symbol  # Recurse


@dataclasses.dataclass
class _AssignedSymbol(_SymbolDefinition):
  pass


class _DeclaredSymbol(_SymbolDefinition):
  pass


class _GlobalAssignementExtractor(ast.NodeVisitor):

  def __init__(self, module_name: str):
    self._module_name = module_name
    self.symbols: dict[str, _SymbolDefinition] = {}

    self._should_capture = None

  @contextlib.contextmanager
  def _capture(self, node: ast.AST):
    assert not self._should_capture
    self._should_capture = _AssignedSymbol(
        module_name=self._module_name,
        start=node.lineno,
        end=node.end_lineno,
    )
    yield
    assert self._should_capture
    self._should_capture = None

  # TODO(epot): Support `ast.NamedExpr` (`:=`)

  def visit_Name(self, node: ast.Name):  # x = y
    if self._should_capture:
      self.symbols[node.id] = self._should_capture

  def visit_Assign(self, node: ast.Assign):  # x = y
    with self._capture(node):
      for target in node.targets:
        self.visit(target)

  def visit_AnnAssign(self, node: ast.AnnAssign):  # x: int = y
    with self._capture(node):
      self.visit(node.target)

  # `import xxx as yyy` only import modules

  def visit_ImportFrom(self, node):
    module = node.module or ''
    for alias in node.names:
      alias_name = alias.asname or alias.name
      self.symbols[alias_name] = _ImportedSymbol(
          module_name=self._module_name,
          start=node.lineno,
          end=node.end_lineno,
          import_module_name=module,
          symbol_name=alias.name,
      )
    self.generic_visit(node)

  def visit_FunctionDef(self, node: ast.FunctionDef):
    self.symbols[node.name] = _DeclaredSymbol(
        module_name=self._module_name,
        start=node.lineno,
        end=node.end_lineno,
    )
    # Do not recurse inside function

  def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
    self.visit_FunctionDef(node)
    # Do not recurse inside function

  def visit_ClassDef(self, node: ast.ClassDef):
    self.visit_FunctionDef(node)
    # Do not recurse inside function

  def generic_visit(self, node):
    if isinstance(
        node,
        (
            ast.Attribute,  # x.y
            ast.Subscript,  # x[0]
        ),
    ):
      # Skip recursing inside functions,...
      return
    return super().generic_visit(node)


@functools.cache
def extract_symbols(module_name: str) -> dict[str, _SymbolDefinition]:
  path = import_utils.module_path(module_name)
  return _extract_assignement_lines(path.read_text(), module_name)


@functools.cache
def extract_last_symbol(
    module_name: str, name: str
) -> _SymbolDefinition | None:
  try:
    symbols = extract_symbols(module_name)
  except Exception as e:
    epy.reraise(e, prefix=f'{module_name}:{name}: ')
  if name not in symbols:
    return
  symbol = symbols[name]
  symbol = symbol.last_project_symbol
  return symbol


def _extract_assignement_lines(
    file_content: str,
    module_name: str,
) -> dict[str, _SymbolDefinition]:
  tree = ast.parse(file_content)

  extractor = _GlobalAssignementExtractor(module_name=module_name)
  extractor.visit(tree)
  return extractor.symbols
