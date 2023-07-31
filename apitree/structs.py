"""."""

import dataclasses

from etils import edc

from apitree.ext import github_link


@edc.dataclass
@dataclasses.dataclass
class ModuleInfo:
  """.

  Attributes:
    api: Entry point of the API
    module_name: What to include
    alias: Short name of the module
    github_url: GitHub repository url (for the GitHub links)
    path_rel_to_imports: By default, get the path relative to the repo.
    should_be_packages: Extra modules that should be concidered package
  """

  api: str
  module_name: str = None
  alias: str = None
  github_url: str = None
  path_rel_to_imports: bool = False
  should_be_packages: list[str] = dataclasses.field(default_factory=list)

  def __post_init__(self):
    if self.module_name is None:
      self.module_name = self.api
    if self.alias is None:
      self.alias = self.module_name
    if self.github_url is None:
      self.github_url = github_link.get_github_url()
