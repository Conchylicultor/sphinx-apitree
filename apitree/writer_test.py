"""."""

import pytest
# import visu3d
from etils import enp, epath, epy, lazy_imports

from apitree import structs, tree_extractor, writer


# TODO(epot): Allow to generate doc even outside the projects
@pytest.mark.skip
def test_api_tree():
  writer.write_doc(
      structs.ModuleInfo(
          module_name='etils.lazy_imports',
          api='etils.lazy_imports',
          alias='lazy_imports',
      )
  )


if __name__ == '__main__':
  pytest.main()
  # writer.write_doc(visu3d)

  # print(tree_extractor.get_api_tree(lazy_imports))
  # print(tree_extractor.get_api_tree(epy))
  # print(tree_extractor.get_api_tree(enp))
  # print(tree_extractor.get_api_tree(epath))
