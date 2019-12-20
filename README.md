# Hot Penguin (httpgui)
----

`httpgui` is a Python library for thin HTML and SVG GUIs with
*all* logic and event handling in server-side Python.

## Example: Hello world!

```python
import httpgui

def clicked(ctx):
    print("greeting clicked")
    ctx.page.update({"greeting": "Hello world!"})

while 1:
    session = httpgui.new_session(':8080', env=globals())
    first_page = session.new_page(
        '<p id="greeting" python-onclick="clicked(ctx)">(click me!)</p>')
```
