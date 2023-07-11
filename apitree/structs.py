"""."""

import dataclasses

from etils import edc


@edc.dataclass
@dataclasses.dataclass
class ModuleInfo:
  """.

  Attributes:
    api: Entry point of the API
    module_name: What to include
    alias: Short name of the module
  """

  module_name: str
  api: str = None
  alias: str = None

  def __post_init__(self):
    if self.api is None:
      self.api = self.module_name
    if self.alias is None:
      self.alias = self.module_name
