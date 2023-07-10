"""

TODO(epot): Replace all `my_module.XXX` by `:ref:...` to link to the API doc.

```
def postprocess(app, doctree):
    # Traverse the doctree and modify the content as needed
    for node in doctree.traverse():
        if isinstance(node, nodes.Text):
            # Apply your post-processing logic to the node's text
            node.astext = node.astext.upper()

def setup(app):
    app.connect('doctree-resolved', postprocess)
```

"""
