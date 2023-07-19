import functools
import pathlib
import tomllib
from typing import Any

import sphinx
from etils import epath, epy

from apitree import structs, writer
from apitree.ext import github_link


def setup(app, *, callbacks):
  for callback in callbacks:
    callback()


def make_project(
    *,
    modules: dict[str, str] | structs.ModuleInfo,
    includes_paths: dict[str, str] = {},
    globals: dict[str, Any],
) -> None:
  """Setup the `conf.py`.

  Args:
    modules: Top module names to document.
    includes_paths: Mapping to external files to `docs/` path (e.g.
      `my_module/submodule/README.md` to `submodule.md`). By default, only
      files inside `docs/...` can be read
    globals: The `conf.py` `globals()` dict. Will be mutated.
  """
  docs_dir = epath.Path(globals['__file__']).parent  # <repo>/docs/
  repo_dir = docs_dir.parent

  project_name = _get_project_name(repo_dir=repo_dir)

  globals.update(
      # Project information
      project=project_name,
      copyright=f'2023, {project_name} authors',
      author=f'{project_name} authors',
      # General configuration
      extensions=[
          'myst_nb',  # Notebook support
          'sphinx.ext.napoleon',  # Numpy-style docstrings
          'sphinx.ext.autodoc',  # API Doc generator
          'sphinx.ext.linkcode',  # Links to GitHub
          # Others:
          # 'sphinx_autodoc_typehints',
          # 'sphinx.ext.linkcode',
          # 'sphinx.ext.inheritance_diagram',
          # 'autoapi.extension',
          # 'myst_parser',
          # API Tree
          'apitree.ext.docstring',  # Fix bad ```python md formatting
          'apitree.ext.auto_ref',  # Add cross ref for inline code
      ],
      exclude_patterns=[
          '_build',
          'jupyter_execute',
          'Thumbs.db',
          '.DS_Store',
      ],
      # HTML output
      html_theme='sphinx_book_theme',
      # Other themes:
      # 'alabaster' (default)
      # 'sphinx_material'
      # 'sphinx_book_theme' (used by Jax)
      html_title=project_name,
      # TODO(epot): Instead should have a self-reference TOC
      html_theme_options={'home_page_in_toc': True},
      # -- Extensions ---------------------------------------------------
      # ---- myst -------------------------------------------------
      myst_heading_anchors=3,
      # ---- myst_nb -------------------------------------------------
      nb_execution_mode='off',
      # ---- autodoc -------------------------------------------------
      autodoc_typehints_format='fully-qualified',  # `x.y.MyClass`
      autodoc_default_options={
          'members': True,
          'show-inheritance': True,
          'member-order': 'bysource',
          'undoc-members': True,
      },
      # Register hooks
      setup=functools.partial(
          setup,
          callbacks=[
              functools.partial(
                  _write_api_doc, docs_dir=docs_dir, modules=modules
              ),
              functools.partial(
                  _write_include_paths,
                  repo_dir=repo_dir,
                  docs_dir=docs_dir,
                  includes_paths=includes_paths,
              ),
          ],
      ),
      # ---- linkcode -------------------------------------------------
      linkcode_resolve=github_link.linkcode_resolve,
  )


def _write_api_doc(
    *,
    docs_dir: pathlib.Path,
    modules: dict[str, str] | structs.ModuleInfo,
):
  api_dir = docs_dir / 'api'
  if api_dir.exists():
    api_dir.rmtree()
  api_dir.mkdir()

  if isinstance(modules, dict):
    modules = [
        structs.ModuleInfo(alias=k, module_name=v) for k, v in modules.items()
    ]
  if isinstance(modules, structs.ModuleInfo):
    modules = [modules]

  for module_info in modules:
    writer.write_doc(module_info, root_dir=api_dir)


def _write_include_paths(
    *,
    repo_dir: pathlib.Path,
    docs_dir: pathlib.Path,
    includes_paths: dict[str, str],
):
  del repo_dir  # Could dynamically compute the `../../../`
  for repo_path, doc_path in includes_paths.items():
    # repo_dir.parent / 'etils'
    content = epy.dedent(
        f"""
        ```{{include}} ../{repo_path}
        ```
        """
    )
    docs_dir.joinpath(doc_path).write_text(content)


def _get_project_name(repo_dir):
  # TODO(epot): This hardcode too much assumption on the program
  path = repo_dir / 'pyproject.toml'
  info = tomllib.loads(path.read_text())
  return info['project']['name']
