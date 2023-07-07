# sphinx-apitree

`apitree` is a small library to generate a ready-to-use documentation with minimal friction!

`apitree` takes care of everything, so you can only focus on the code.

## Usage

In `docs/conf.py`, replace everything by:

```python
import apitree

apitree.make_project(
    project_name='my_module',
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
  * Do not require `__all__`
  * Add expandable toc tree with all symbols
* ...

## Installation in a project

1.  In `pyproject.toml`

    ```toml
    [project.optional-dependencies]
    # Installed through `pip install .[docs]`
    docs = [
        # Install `apitree` with all extensions (sphinx, theme,...)
        "sphinx-apitree[ext] @ https://github.com/conchylicultor/sphinx-apitree",
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

* https://github.com/google-research/visu3d
* https://github.com/google-research/dataclass_array
* https://github.com/google-research/etils
