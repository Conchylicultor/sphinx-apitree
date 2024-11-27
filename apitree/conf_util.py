import functools
import os
import pathlib
import sys
import tomllib
from typing import Any

import sphinx
from etils import epath, epy

from apitree import import_utils, structs, writer
from apitree.ext import github_link


def setup(app, *, callbacks):
  for callback in callbacks:
    callback()


def make_project(
    *,
    modules: dict[str, str] | structs.ModuleInfo | list[structs.ModuleInfo],
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

  # TODO(epot): Fragile if one of the module is already imported.
  # If so, should check that imported modules are
  # `import_utils.belong_to_project`
  # Allow import without installing the project first (dependencies
  # still have to be installed.
  sys.path.insert(0, os.fspath(repo_dir))

  # API generator
  api_ext = 'sphinx.ext.autodoc'
  api_ext_config = dict(
      autodoc_typehints_format='fully-qualified',  # `x.y.MyClass`
      autodoc_default_options={
          'members': True,
          'show-inheritance': True,
          'member-order': 'bysource',
          'undoc-members': True,
      },
      maximum_signature_line_length=60,
  )

  # Uncomment to try autoapi
  # api_ext = 'autoapi.extension'
  # api_ext_config = dict(
  #     autoapi_dirs=[f'../{project_name}'],
  #     autoapi_ignore=['*migrations*', '*_test.py'],
  #     autoapi_keep_files=True,
  #     autoapi_python_use_implicit_namespaces=True,
  # )

  globals.update(
      # Project information
      project=project_name,
      copyright=f'2023, {project_name} authors',
      author=f'{project_name} authors',
      # General configuration
      extensions=[
          api_ext,  # API Doc generator
          'myst_nb',  # Notebook support
          'sphinx.ext.napoleon',  # Numpy-style docstrings
          'sphinx.ext.linkcode',  # Links to GitHub
          # Others:
          # 'sphinx_autodoc_typehints',
          # 'sphinx.ext.linkcode',
          # 'sphinx.ext.inheritance_diagram',
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
      # ---- api extension -------------------------------------------------
      **api_ext_config,
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
    modules: dict[str, str] | structs.ModuleInfo | list[structs.ModuleInfo],
):
  api_dir = docs_dir / 'api'
  if api_dir.exists():
    api_dir.rmtree()
  api_dir.mkdir()

  if isinstance(modules, dict):
    modules = [structs.ModuleInfo(alias=k, api=v) for k, v in modules.items()]
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
  for repo_path, doc_path in includes_paths.items():
    src_path = repo_dir / repo_path
    dst_path = docs_dir / doc_path
    match src_path.suffix:
      case '.md':
        # repo_dir.parent / 'etils'
        # Could dynamically compute the `../../../`
        content = epy.dedent(
            f"""
            ```{{include}} ../{repo_path}
            ```
            """
        )
        dst_path.write_text(content)
      case '.ipynb':
        dst_path.write_bytes(src_path.read_bytes())
      case default:
        raise ValueError(f'Invalid suffix: {default}')


def _get_project_name(repo_dir):
  # TODO(epot): This hardcode too much assumption on the program
  path = repo_dir / 'pyproject.toml'
  info = tomllib.loads(path.read_text())
  return info['project']['name']
