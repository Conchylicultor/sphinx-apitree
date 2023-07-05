from apitree import tree_extractor, writer

if __name__ == '__main__':
  import visu3d

  writer.write_doc(visu3d)

  import etils
  from etils import enp, epath, epy

  print(tree_extractor.get_api_tree(epy))
  print(tree_extractor.get_api_tree(enp))
  print(tree_extractor.get_api_tree(epath))
