import importlib
import pathlib
from typing import Any

import tomllib

from apitree import writer
from apitree.ext import docstring


def setup(app):
  # Fix bad ```python md formatting
  docstring.setup(app)


def make_project(
    modules: dict[str, str],
    globals: dict[str, Any],
):
  project_name = _get_project_name()

  for alias, module_name in modules.items():
    module = importlib.import_module(module_name)

    writer.write_doc(module, alias=alias)

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
          # Others:
          # 'sphinx_autodoc_typehints',
          # 'sphinx.ext.linkcode',
          # 'sphinx.ext.inheritance_diagram',
          # 'autoapi.extension',
          # 'myst_parser',
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
      setup=setup,
  )


def _get_project_name():
  # TODO(epot): This hardcode too much assumption on the program
  path = pathlib.Path(__file__).parent.parent / 'pyproject.toml'
  info = tomllib.loads(path.read_text())
  return info['project']['name']
