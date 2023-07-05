import inspect


class Signature:

  def __init__(self, fn) -> None:
    pass

  # TODO(epot): 1-line description


def parse_fn(fn):
  sig = inspect.signature(fn)
