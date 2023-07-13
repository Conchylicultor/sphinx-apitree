import ast
import contextlib
import dataclasses
import inspect
import types


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


class _GlobalAssignementExtractor(ast.NodeVisitor):

  def __init__(self):
    self.symbols: dict[str, int] = {}

    self._should_capture = False

  @contextlib.contextmanager
  def _capture(self):
    assert not self._should_capture
    self._should_capture = True
    yield
    assert self._should_capture
    self._should_capture = False

  def visit_Name(self, node: ast.Name):  # x = y
    if self._should_capture:
      self.symbols[node.id] = node.lineno

  def visit_Assign(self, node: ast.Assign):  # x = y
    with self._capture():
      for target in node.targets:
        self.visit(target)

  def visit_AnnAssign(self, node: ast.AnnAssign):  # x: int = y
    with self._capture():
      self.visit(node.target)

  def generic_visit(self, node):
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
            ast.Attribute,  # x.y
            ast.Subscript,  # x[0]
        ),
    ):
      # Skip recursing inside functions,...
      return
    return super().generic_visit(node)


def extract_assignement_lines(file_content: str) -> dict[str, int]:
  tree = ast.parse(file_content)

  extractor = _GlobalAssignementExtractor()
  extractor.visit(tree)
  return extractor.symbols
