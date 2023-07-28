# sphinx-apitree

[![Unittests](https://github.com/conchylicultor/sphinx-apitree/actions/workflows/pytest_and_autopublish.yml/badge.svg)](https://github.com/conchylicultor/sphinx-apitree/actions/workflows/pytest_and_autopublish.yml)
[![PyPI version](https://badge.fury.io/py/sphinx-apitree.svg)](https://badge.fury.io/py/sphinx-apitree)


`apitree` is a small library to generate a ready-to-use documentation with minimal friction!

`apitree` takes care of everything, so you can only focus on the code.

## Usage

In `docs/conf.py`, replace everything by:

```python
import apitree

apitree.make_project(
    # e.g. `import visu3d as v3d` -> {'v3d': 'visu3d'}
    project_name={'alias': 'my_module'},
    globals=globals(),
)
```

Then to generate the doc:

```sh
sphinx-build -b html docs/ docs/_build
```

To add `api/my_module/index` somewhere in your toctree, like:

```md
..toctree:
  :caption: API

  api/my_module/index
```

## Features

* All included: Single function call include the theme, the API generation,...
* Auto-generate the API tree:
  * Do not require `__all__` (smart detect of which symbols are documented)
  * Add expandable toc tree with all symbols
* Add links to `GitHub`.
* Markdown (`.md`) / Jupyter (`.ipynb`) support out of the box
* Auto-cross-references (Just annotate markdown inline-code `my_symbol` and links are auto-added)
* Contrary to `autodoc` and `apitree`, it also document:
  * Type annotations (`Union[]`, ...)
  * Attributes
* ...

## Installation in a project

1.  In `pyproject.toml`

    ```toml
    [project.optional-dependencies]
    # Installed through `pip install .[docs]`
    docs = [
        # Install `apitree` with all extensions (sphinx, theme,...)
        "sphinx-apitree[ext]",
    ]
    ```

1.  In `.readthedocs.yaml`

    ```yaml
    sphinx:
    configuration: docs/conf.py

    python:
    install:
        - method: pip
        path: .
        extra_requirements:
            - docs
    ```

## Options

By default, `apitree` tries to infer everything automatically. However there's sometimes
times where the user want to overwrite the default choices.

*   Package vs module: By default, all `__init__.py` define the public API (imports documented), while
    the modules (`module.py`) define the implementation (imports not documented).
    You can explicitly mark a module as package, so it's import are documented, by adding in the
    module definition:

    ```python
    __apitree__ = dict(
        is_package=True,
    )
    ```

## Examples of projects using apitree

* https://github.com/google-research/visu3d (https://visu3d.readthedocs.io/)
* https://github.com/google-research/dataclass_array (https://dataclass-array.readthedocs.io/)
* https://github.com/google-research/etils (https://etils.readthedocs.io/)
* https://github.com/google-research/kauldron (https://kauldron.readthedocs.io/)

Generated with:

```
echo start \
&& cd ../visu3d          && sphinx-build -b html docs/ docs/_build \
&& cd ../dataclass_array && sphinx-build -b html docs/ docs/_build \
&& cd ../etils           && sphinx-build -b html docs/ docs/_build \
&& cd ../kauldron        && sphinx-build -b html docs/ docs/_build \
&& echo finished
```
