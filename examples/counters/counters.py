"""
counters.py - shared counters configured and managed by urls

Create new counter URL: /new/COUNTER-NAME/ELEMENT-1/...
Use a counter URL: /count/COUNTER-NAME
Delete a counter URL: /del/COUNTER-NAME

Copy a counter with values: /copy/FROM-COUNTER-NAME/TO-COUNTER-NAME
Zero a counter: /zero/COUNTER-NAME
"""

import _thread
import copy
import html
import pickle
import sys
import time
import urllib.parse

import httpgui
httpgui.log = lambda msg: sys.stderr.write(msg + "\n")

html_counter_header = """
<style>
.t{font: 100px sans-serif; color: black;}
.b{font: 120px sans-serif; color: green;}
</style>
<table class="t">
"""

html_counter_footer = """
</table>
"""

html_bad_url = "Bad URL. Better luck next time."
html_bad_url_counter_exists = "Bad URL. Counter already exists."
html_bad_url_counter_does_not_exist = "Bad URL. Counter does not exists."
html_bad_url_unknown_command = "Bad URL. Unknown command. Try /help."
html_counter_deleted = "Counter deleted."
html_help = "<pre>Help\n" + __doc__ + "\n</pre>"

class Counter:
    def __init__(self, name):
        self.name = name
        self.current = [] # list of [key_string, value_int] pairs
        self.history = []

def error(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

def gen_html(counter):
    html = [html_counter_header]
    html.append('<p class="t">%(name)s</p>' % counter.__dict__)
    for elt_id, (key, value) in enumerate(counter.current):
        html_elt = ('<tr>'
                    '<td><input type="button" value="&plus;" class="b" python-onclick()="add(ctx, %(elt_id)d, 1)"/></td>'
                    '<td id="v%(elt_id)d" align="right">%(value)s</td>'
                    '<td><input type="button" value="&minus;" class="b" python-onclick()="add(ctx, %(elt_id)d, -1)"/></td>'
                    '<td>%(key)s</td></tr>') % locals()
        html.append(html_elt)
    html.append(html_counter_footer)
    return "\n".join(html)

def add(ctx, elt_id, amount):
    ctx.session.counter.current[elt_id][1] += amount
    bad_sessions = []
    for session, counter_id in _sessions.items():
        if counter_id == ctx.session.counter.name:
            try:
                session.page().update({"v" + str(elt_id): str(ctx.session.counter.current[elt_id][1]),
                                       })
            except:
                bad_sessions.append(session)
    for session in bad_sessions:
        del _sessions[session]
    pickle.dump(_counters, open("counters.pickle", "wb"))

_counters = {} # {counter_id: Counter_instance}
_sessions = {} # {session: counter_id}

if __name__ == "__main__":
    try:
        _counters = pickle.load(open("counters.pickle", "rb"))
    except:
        pass
    httpgui.log = lambda msg: sys.stderr.write(time.strftime("%F %T ") + msg + "\n")
    try:
        host_port = sys.argv[1]
    except:
        error('Usage: chat HOST:PORT\nExample: counters 0.0.0.0:5555')
    while 1:
        session = httpgui.new_session(host_port, env=globals())

        if session.path().split("/", 1)[1].startswith("help"):
            session.new_page(html_help, static=True)
            continue

        try:
            if session.path().count("/") == 2:
                _, url_cmd, url_counter_id = session.path().split("/", 2)
                url_rest = ""
            else:
                _, url_cmd, url_counter_id, url_rest = session.path().split("/", 3)
        except:
            session.new_page(html_bad_url, static=True)
            continue

        counter_id = urllib.parse.unquote(url_counter_id)
        url_rest = urllib.parse.unquote(url_rest)
        if url_cmd in ["n", "new"]:
            new_counter_spec = url_rest
            if counter_id in _counters:
                session.new_page(html_bad_url_counter_exists, static=True)
                continue
            counter = Counter(counter_id)
            for elt_spec in new_counter_spec.split("/"):
                elt_val = 0
                counter.current.append([elt_spec, elt_val])
            _counters[counter_id] = counter
            session.new_page("")
            # redirect to "cont" counter usage so that the user gets a nice url
            session.page().update({"js": "location.replace('/count/%s')" % (counter_id,)})
            continue
        elif url_cmd in ["c", "count", "cont", "continue"]:
            if not counter_id in _counters:
                session.new_page(html_bad_url_counter_does_not_exist, static=True)
                continue
        elif url_cmd in ["del", "delete"]:
            if not counter_id in _counters:
                session.new_page(html_bad_url_counter_does_not_exist, static=True)
                continue
            closed_sessions = []
            session.new_page(html_counter_deleted, static=True)
            for _session in _sessions:
                if counter_id == _session.counter_id:
                    _session.new_page(html_counter_deleted, static=True)
                    closed_sessions.append(_session)
            time.sleep(1)
            for _session in closed_sessions:
                del _sessions[_session]
            del _counters[counter_id]
            continue
        elif url_cmd in ["cp", "copy"]:
            if not counter_id in _counters:
                session.new_page(html_bad_url_counter_does_not_exist, static=True)
                continue
            target_counter_id = url_rest
            _counters[target_counter_id] = copy.deepcopy(_counters[counter_id])
            _counters[target_counter_id].name = target_counter_id
            session.new_page("")
            session.page().update({"js": "location.replace('/count/%s')" % (target_counter_id,)})
        elif url_cmd in ["z", "zero"]:
            if not counter_id in _counters:
                session.new_page(html_bad_url_counter_does_not_exist, static=True)
                continue
            for elt in _counters[counter_id].current:
                elt[1] = 0
            session.new_page("")
            session.page().update({"js": "location.replace('/count/%s')" % (counter_id,)})
        else:
            session.new_page(html_bad_url_unknown_command, static=True)
            continue
        session.counter_id = counter_id
        session.counter = _counters[counter_id]
        _sessions[session] = counter_id
        session.new_page(gen_html(session.counter), env=globals())
