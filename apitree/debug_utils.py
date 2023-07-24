import contextlib
import traceback


@contextlib.contextmanager
def print_error():
  try:
    yield
  except Exception as e:
    raise RuntimeError(f'\n{traceback.format_exc()}')
