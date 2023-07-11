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

* Theme
* Auto-generate the API tree, with better features
  * Do not require `__all__` (smart detect of which symbols are documented)
  * Add expandable toc tree with all symbols
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

## Examples of projects using apitree

* https://github.com/google-research/visu3d (https://visu3d.readthedocs.io/)
* https://github.com/google-research/dataclass_array (https://dataclass-array.readthedocs.io/)
* https://github.com/google-research/etils (https://etils.readthedocs.io/)
* https://github.com/google-research/kauldron (https://kauldron.readthedocs.io/)
