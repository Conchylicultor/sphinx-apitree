import textwrap

from apitree import ast_utils


def test_extract_import_symbols():
  symbols = ast_utils.parse_global_imports(
      textwrap.dedent(
          """
          import a
          import a2.b.c
          from b.c import (
              x, y)
          from d import z as alias_z
          from e import *
          from f.g import h as alias_h, i

          with some_symbol():
            if AA:
              import inside_cm  # Detected
            else:
              import inside_cm2

          def fn():
            import inside_fn  # Ignored
          """
      )
  )

  assert symbols == [
      ast_utils.ImportAlias(namespace='a', alias='a'),
      ast_utils.ImportAlias(namespace='a2.b.c', alias='a2'),
      ast_utils.ImportAlias(namespace='b.c.x', alias='x'),
      ast_utils.ImportAlias(namespace='b.c.y', alias='y'),
      ast_utils.ImportAlias(namespace='d.z', alias='alias_z'),
      ast_utils.ImportAlias(namespace='e.*', alias='*'),
      ast_utils.ImportAlias(namespace='f.g.h', alias='alias_h'),
      ast_utils.ImportAlias(namespace='f.g.i', alias='i'),
      ast_utils.ImportAlias(namespace='inside_cm', alias='inside_cm'),
      ast_utils.ImportAlias(namespace='inside_cm2', alias='inside_cm2'),
  ]
