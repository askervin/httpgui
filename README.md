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

## How it works

1. `httpgui.new_session` returns a `Session` instance when a browser
   connects to the port.

   At this point `httpgui` sends the basic logic to the browser. It
   makes the browser request for more information and evaluate
   whatever code it gets as a response.

2. `session.new_page` sends HTML to the browser and returns a `Page`
   instance. There is one extension to normal HTML: you can attach a
   Python function call to any DOM Event (onclick, onmouseover, ...)
   using `python-EVENT` attribute (`python-onclick`,
   `python-onmouseover`, ...).

3. Python function calls in HTML are evaluated in the environment
   defined when creating the session (`env`). A special function
   parameter `ctx` in calls contains `Session` and `Page` instances,
   allowing handling of multiple sessions and pages per session
   concurrently.

## Snippets

### Parsing URL and showing static pages

```python
# Browse to location http://localhost:5555/pages/page1.html
import httpgui
import urllib
while 1:
    session = httpgui.new_session(":5555")
    if session.path() == "/pages/page1.html":
        session.new_page('go to <a href="page2.html">static page 2</a>', static=True)
    elif session.path() == "/pages/page2.html":
        session.new_page('go to <a href="page1.html">static page 1</a>', static=True)
    else:
        session.new_page('unknown path: <pre>%s</pre>' % urllib.parse.quote(session.path()))
```

### Updating dynamic page contents

```python
import httpgui
import time
session = httpgui.new_session(":5555")
page = session.new_page('<p>Server time:</p><pre id="server-time"></pre>')
while True:
    page.update({"server-time": time.strftime("%F %T")})
    time.sleep(1)
```

## Examples

- [chat.py](examples/chat/chat.py) implements a multiroom chat server
  where users can edit what has been said and see who are currently
  typing.

- [counters.py](examples/counters/counters.py) implements a page where
  users can increment and decrement counters that are defined in the
  URL. There can be many users using the same counter at the same
  time.

- [html-inputs.py](examples/html-inputs/html-inputs.py) demonstrates
  reading values and statuses of HTML input elements on the browser
  (`Page.current`).
