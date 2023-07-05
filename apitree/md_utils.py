from etils import epy


class Table:

  def __init__(self, *, header):
    self._lines = epy.Lines()
    self._lines += '| ' + ' | '.join(header) + ' |'
    self._lines += ' | '.join('---' for _ in header)

  def add_row(self, *row: str):
    self._lines += ' | '.join(row)

  def make(self) -> str:
    return self._lines.join()
