# Hot Penguin (httpgui) - Python GUI over HTTP without Javascript
# Copyright (c) 2019, Antti Kervinen <antti.kervinen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms and conditions of the GNU Lesser General Public
# License, version 2.1, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St - Fifth Floor, Boston, MA
# 02110-1301 USA.

"""Hot Penguin (httpgui) - Python GUI over HTTP without Javascript

Example: interactive hello world:

import httpgui

def clicked(ctx):
    print("clicked")
    ctx.page.update({"greeting": "Hello world!"})

while 1:
    session = httpgui.new_session(':8080', env=globals())
    first_page = session.new_page(
        '<p id="greeting" python-onclick="clicked(ctx)">(click me!)</p>')
"""

import base64
import json
import re
import socket
import _thread
import time
import traceback
import types
import urllib.parse

class ProtocolError(Exception): pass

_browser_side_js = """
timer_interval_ms = %(timer_interval_ms)s; // milliseconds, zero disables timer
pending_server_event = %(pending_server_event)s; // true or false, 1 or 0

tick_count = 0;
server_event_count = 0;

session_id = "%(session)s";

function send_to_server(url, content, callback) {
    if (session_id == "")
        return;

    session_url = "/" + session_id + "/" + url;

    var xmlHttp = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("MSXML2.XMLHTTP.3.0");

    // xmlHttp = new XMLHttpRequest(); // IE does not work this way.
    if (callback != null) {
        xmlHttp.onreadystatechange = function() {
            if (xmlHttp.readyState == 4) callback(xmlHttp);
        }
    }
    if (content == null) xmlHttp.open("GET", session_url, true);
    else xmlHttp.open("POST", session_url, true);
    xmlHttp.send(content);
}

function eval_response(xmlHttp) {
    eval(xmlHttp.responseText);
}

function eval_time_response(xmlHttp) {
    if (xmlHttp.status != 200) {
        console.log("timer_tick: stopped at " + tick_count + ", last response status: " + xmlHttp.status);
        return;
    }
    eval(xmlHttp.responseText);
    tick_count += 1;
    if (timer_interval_ms > 0)
        setTimeout(timer_tick, timer_interval_ms);
}

function event_received(xmlHttp) {
    if (xmlHttp.status != 200) {
        console.log("wait_server_event: stopped at " + server_event_count + ", last response status: " + xmlHttp.status);
        return;
    }
    eval(xmlHttp.responseText);
    wait_server_event();
}

function wait_server_event() {
    send_to_server("wait_server_event(" + server_event_count + ")", null, event_received);
    server_event_count += 1;
}

function timer_tick() {
    if (timer_interval_ms > 0)
        send_to_server("timer_tick(ctx, " + tick_count + ")", "{}", eval_time_response);
}

function properties_to_dict(obj, attr_list=undefined) {
    var dict = {};
    for (var property in obj) {
        if (attr_list != undefined && !attr_list.includes(property))
            continue;
        if (typeof obj[property] == "number" ||
            typeof obj[property] == "boolean" ||
            typeof obj[property] == "string") {
            dict[property.toString()] = obj[property];
        }
    }
    return dict;
}

function send_event(event_string, event, elt, event_attr_list) {
    var event_dict = properties_to_dict(event, event_attr_list);
    if (event_attr_list == undefined || event_attr_list.includes("target")) {
        var target_dict = properties_to_dict(event.target);
        event_dict["target"] = target_dict;
    }
    if (event_attr_list == undefined || event_attr_list.includes("elt")) {
        var elt_dict = properties_to_dict(elt);
        event_dict["elt"] = elt_dict;
        var elt_bbox = {};
        try {
            elt_bbox = properties_to_dict(elt.getBBox());
        } catch (err) {
            try {
                elt_bbox = properties_to_dict(elt.getBoundingClientRect());
            } catch (err) {
            }
        }
        event_dict["elt"]["bbox"] = elt_bbox;
    }
    last_sent_event = event;
    var call_env = {"event": event_dict};
    send_to_server(event_string, JSON.stringify(call_env), eval_response);
}

// prevent some default behavior in order to keep control on app
window.onkeydown = function(e) {
  if (e.keyCode == 8 && e.target == document.body)
    e.preventDefault();
}

setTimeout(timer_tick, 1);
if (pending_server_event) {
    wait_server_event();
}
"""

_html_basepage='''
<html><body>
<div id="rootdiv">
%s
</div>
<script language="JavaScript" type="text/javascript">
%s
</script>
</body></html>
'''

default_favicon = base64.b64decode('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')

_re_timer_tick = re.compile(rb'timer_tick\(ctx, [0-9]+\)')
_re_python_attr = re.compile(r' python-(?P<js_event>on[a-zA-Z0-9]*)(\((?P<event_attrs>[a-zA-Z0-9, ]*)\))?="(?P<python>[^"]*)"')
_re_python_event = re.compile(r'python-(?P<js_event>on[a-zA-Z0-9]*)')

def log(msg): # override this function to catch httpgui log somewhere else
    pass

def set_logfile(file_obj):
    global log
    log = lambda msg: (file_obj.write(str(msg) + "\n"), file_obj.flush())

def _close(conn):
    try:
        conn.close()
    except:
        pass

def _http_send_ok(conn, s):
    if isinstance(s, bytes):
        s_bytes = s
    else:
        s_bytes = bytes(s, "utf-8")
    resp = (b"HTTP/1.1 200 OK\r\n"
            b"Server: Hot Penguin\r\n"
            b"Keep-Alive: timeout=30\r\n"
            b"Connection: Keep-Alive\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-Length: %d\r\n\r\n%s") % (len(s_bytes), s_bytes)
    return conn.sendall(resp)

def _http_send_404(conn, s):
    if isinstance(s, bytes):
        s_bytes = s
    else:
        s_bytes = bytes(s, "utf-8")
    resp = (b"HTTP/1.1 404 Not found\r\n"
            b"Server: Hot Penguin\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Content-Length: %d\r\n\r\n%s") % (len(s_bytes), s_bytes)
    return conn.sendall(resp)

def _http_read(conn):
    if repr(conn) in _http_read._read_too_far:
        data = _http_read._read_too_far[repr(conn)]
        del _http_read._read_too_far[repr(conn)]
    else:
        try:
            data = conn.recv(4096)
        except:
            data = b""
    if data == b"":
        return b""
    if data != b"" and len(data) < 4 and not (data.startswith(b"GET") or data.startswith(b"POST")):
        data += conn.recv(4096)
    if data.startswith(b"POST"): # require content-length in POST
        while not b"content-length" in data.lower():
            data += conn.recv(4096)
        while not b"\r\n\r\n" in data:
            data += conn.recv(4096)
    datarows = data.split(b'\n')
    datalength = 0
    datahead, databody = data, b""
    for row in datarows:
        if row.lower().startswith(b'content-length'):
            datalength = int(row.strip().split()[1])
            datahead, databody = data.split(b'\r\n\r\n', 1)
            break
    while len(databody) < datalength:
        databody += conn.recv(4096)
    if len(databody) > datalength:
        _http_read._read_too_far[repr(conn)] = databody[datalength:]
        databody = databody[:datalength]
    return datahead + b'\r\n\r\n' + databody
_http_read._read_too_far = {}

def _session_id_new():
    session_id =  b".session-%f" % (time.time(),)
    return session_id

def _session_id_valid(session_id):
    if session_id.startswith(b".session-"):
        return True
    else:
        return False

def _path_parse(http_request):
    """parse path from http request"""
    first_line = http_request.split(b'\n', 1)[0] # it's on the first row
    try:
        # between two spaces: GET<space>addr<space>HTTP/1.1
        path = first_line.split(b'GET ')[1].split(b' HTTP/')[0].decode('utf-8')
    except IndexError as e:
        path = ""
    return path

class Protocol(object):
    """
    Server-browser Protocol
    """

    def __init__(self, *a, **kw):
        self.name = "Protocol"
        self._sockets = {}
        self._sid2conn = {} # {session-id: socket_connection}
        self._sid2sess = {} # map session-id's to session objects
        self._allow_new_session_lock = _thread.allocate_lock()
        self._allow_new_session = {} # (host, port) -> [lock1, lock2, ...]
        self._favicon = default_favicon

    def new_session(self, hostspec, **kw):
        """
        Examples:
            # defaults. no timer tick from browser, but always has pending
            # server event request.
            new_session("locahost:9999")

            # browser timer_tick every 100 ms, no pending_server_event requests
            new_session(":9999", timer_interval_ms=100, pending_server_events=0)

            # no polling from server, all events are triggered by user
            new_session(":9999", timer_interval_ms=0, pending_server_events=0)

            # custom favicon.ico
            new_session(":9999", favicon=_my_favicon_data)

            # the default eval env (Python code evaluation context)
            # for user-defined includes all functions and variables in
            # globals().
            new_session(":9999", env=globals())
        """
        try:
            host, port_s = hostspec.split(":")
            port = int(port_s)
        except Exception as e:
            raise Exception("invalid hostspec %r: %s" % (hostspec, e))
        new_session_lock = self._new_session((host, port), **kw)
        new_session_lock.lock.acquire()
        if new_session_lock.sessname == "":
            raise ProtocolError("Cannot accept TCP connections from spec: %s" % (hostspec,))
        else:
            return new_session_lock.sess

    def _new_session(self, host_port, **kw):
        """returns a lock that is acquired when the new session
        has been established"""
        class sessionlock(object): pass
        sl = sessionlock()
        sl.lock = _thread.allocate_lock()
        sl.lock.acquire()
        sl.sessname = ""
        self._allow_new_session_lock.acquire()
        if not host_port in self._allow_new_session:
            # There is no server thread listening to the port.
            # Let's start one.
            self._allow_new_session[host_port] = [sl]
            _thread.start_new_thread(self._http_server, (host_port, kw))
        else:
            # Allow existing server thread, which listens to the given
            # port, accept a new session.
            self._allow_new_session[host_port].append(sl)
        self._allow_new_session_lock.release()
        return sl

    def _new_session_allowed(self, host_port):
        """returns 1 if new session through the port is allowed,
        otherwise 0"""
        self._allow_new_session_lock.acquire()
        if len(self._allow_new_session[host_port]) > 0:
            first_lock = self._allow_new_session[host_port].pop(0)
            self._allow_new_session_lock.release()
            return first_lock
        else:
            self._allow_new_session_lock.release()
            return None

    def close_session(self, session_id):
        if session_id in self._sid2conn:
            _close(self._sid2conn[session_id])
            del self._sid2conn[session_id]
        if session_id in self._sid2sess:
            del self._sid2sess[session_id]

    def _http_server(self, host_port, options):
        # There is one http_server thread for each port that is
        # listened to. These threads start new thread for handling
        # each new tcp connection.
        while 1:
            try:
                conn = self._accept_tcp_connection(host_port)
            except:
                for l in self._allow_new_session[host_port]:
                    l.lock.release()
                break
            # given a tcp connection, start new server thread for
            # that connection in the connection threads, keep track on
            # the number of connections per session session id is
            # carried on every url and it is generated by this server
            # for new sessions

            # URL types:
            # New session: GET /
            # Callback:    POST /session-id/pythoncode (event dict in post data)
            # Erroneous:   all other URLs
            _thread.start_new_thread(self._serve_connection, (conn, host_port, options))

    def _serve_connection(self, conn, host_port, options):
        # Connection handler. This handles http messages received
        # from the connection, establishes new session and
        # routes http messages to the correct sessions.
        log("serving connection to %s from %s" % (host_port, conn.getpeername()))
        while 1:
            data = _http_read(conn)
            if data == b"": # connection lost
                break
            elif b"favicon.ico" in data[:data.find(b'\r\n\r\n')]:
                if not "favicon" in options:
                    _http_send_ok(conn, self._favicon)
                else:
                    _http_send_ok(conn, options['favicon'])
                continue
            session, object_id = self._check_session(data)
            if not session: # this starts a new session
                session_lock = self._new_session_allowed(host_port)
                if not session_lock:
                    _http_send_404(conn, "not taking new sessions right now")
                    break
                else: # register new session and release the lock
                    sess = Session(self, env=options.get("env", None))
                    # THINK: need for cryptic session id?
                    identified_session = _session_id_new()
                    browser_side_js_vars = {
                        'session': str(identified_session, "utf-8"),
                        'timer_interval_ms': 0, # default: no timer tick
                        'pending_server_event': 1 # default: always wait for server messages
                    }
                    # enable changing timer_interval_ms and pending_server_event defaults
                    browser_side_js_vars.update(options)
                    sess._set_session_id(identified_session)
                    sess._set_path(_path_parse(data))
                    self._sid2sess[identified_session] = sess
                    self._sid2conn[identified_session] = conn
                    response = _html_basepage % (
                        "",
                        _browser_side_js % browser_side_js_vars)
                    session_lock.sessname = str(sess)
                    session_lock.sess = sess
                    session_lock.lock.release()
            elif session in self._sid2sess: # now the session is identified
                # check connection validity in response because a
                # browser can use the same tcp connection for
                # different sessions.
                sess = self._sid2sess[session]
                response = sess._handle_http_data(data)
                if response is None:
                    break
                elif response == "wait_server_event":
                    if not sess._delayed_response_conn is None:
                        _http_send_ok(sess._delayed_response_conn, "")
                        sess._delayed_response_conn = None
                    # do not send response to this event now. store the connection
                    # and send response to this connection when there
                    # is something to send
                    # this thread should send the response when ready
                    sess._delayed_response_conn = conn
                    while not sess._to_browser_queue:
                        sess._delayed_response_conn_lock.acquire()
                    sess._to_browser_queue_lock.acquire()
                    try:
                        # no need to lock - this thread already has the lock
                        response = sess._response_from_browser_queue(lock=False)
                        try:
                            _http_send_ok(sess._delayed_response_conn, response)
                        except Exception as e:
                            log("sending ok to a session failed: %s" % (e,))
                            break
                    finally:
                        sess._delayed_response_conn = None
                        sess._to_browser_queue_lock.release()
                    continue
            else: # session cannot be found in session library. strange
                log("invalid session")
                break
            _http_send_ok(conn, response)
        _close(conn)

    def _check_session(self, s):
        """returns id of an session (a non-empty string) or
        an empty string if data seems to start a new session"""
        s = s.split(b'\n', 1)[0] # it's on the first row
        s = s.split(b' ')[1] # between two spaces: GET<space>addr<space>HTTP/1.1
        session_id = b""
        object_id = b""
        try:
            first_slash = s.index(b"/")
            second_slash = s.index(b"/", first_slash + 1)
            session_id = s[first_slash + 1:second_slash]
            object_id = s[second_slash + 1:]
        except ValueError as e:
            pass
        if not _session_id_valid(session_id):
            session_id = b""
        return session_id, object_id

    def _accept_tcp_connection(self, host_port):
        """
        Returns an open socket object.
        """
        if host_port in self._sockets:
            s = self._sockets[host_port]
        else:
            log("binding host, port %r" % (host_port,))
            s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except:
                pass
            s.bind(host_port)
            s.listen(1)
            self._sockets[host_port] = s
        conn, src = s.accept()
        return conn

class Session(object):
    """
    Session handles http requests directed to this session.
    """
    counter = 0

    def __init__(self, protocol, env=None, **kw):
        self.name = str(Session.counter)
        Session.counter += 1
        log("new session %s" % (Session.counter,))
        self._protocol = protocol
        self._pages = {}
        self._to_browser_queue = []
        self._to_browser_queue_lock = _thread.allocate_lock()
        self._active_page = Page(self, "") # a dummy page
        self._delayed_response_conn = None
        self._delayed_response_conn_lock = _thread.allocate_lock()
        self._delayed_response_conn_lock.acquire()
        self._env = env
        self._path = None

    def _set_session_id(self, session_id):
        self._session_id = session_id

    def _set_path(self, path):
        self._path = path

    def path(self):
        """Returns path requested at the beginning of the session."""
        return self._path

    def page(self):
        """Returns active page"""
        return self._active_page

    def new_page(self, html, *funcs_and_envs, **options):
        """Creates new page on browser.

        Parameters:
          html (string):  html content for the page

          additional parameters (optional):
            function:             makes python function callable from events.
                                  Example: new_page(..., my_func)
                                  adds {"my_func": my_func} to eval env.
            dict ({name: value}): makes names available in eval env.
                                  Example: {"my_func": my_function}

                                  Names that start with "python-" are
                                  special cases: they are handled as global
                                  event handlers on the page and are assocated
                                  to Python function callback calls:
                                  Example: {"python-onkeydown": "key_down(ctx)"}

          keyword parameters (optional):
            pending_server_event (int, 0 or 1)
                                  override Session parameter when showing this page
            timer_interval_ms (int)
                                  override Session parameter when showing this page
            static (bool)
                                  send a page that cannot be updated anymore.
                                  Sets timer_interval_ms=0,
                                  pending_server_event=0, and
                                  session_id="".
        """
        new_page = Page(self, html, **options)
        self._pages[str(new_page)] = new_page
        self.set_active(str(new_page))
        funcname_func = {}
        if self._env:
            new_page.update_env(self._env)
        for func_or_env in funcs_and_envs:
            if isinstance(func_or_env, dict):
                new_page.update_env(func_or_env)
            elif isinstance(func_or_env, types.FunctionType):
                funcname_func[func_or_env.__name__] = func_or_env
            else:
                raise ValueError('invalid parameter %r, expected function or eval env dictionary' % (func_or_env,))
        if funcname_func:
            new_page.update_env(funcname_func)
        return new_page

    def set_active(self, page_id):
        """
        Activates page_id. The browser should be evaluating (eval)
        responses.
        """
        if not page_id in self._pages:
            raise Exception("Page %s not found in %s" %
                            (page_id, repr(self)))
        self._active_page = self._pages[page_id]
        # TODO: add JS code that changes pending_server_event and timer_interval_ms
        js_to_browser = []
        if not self._active_page._pending_server_event is None:
            js_to_browser.append("pending_server_event = %s;" % (self._active_page._pending_server_event,))
        if not self._active_page._timer_interval_ms is None:
            js_to_browser.append("timer_interval_ms = %s;" % (self._active_page._timer_interval_ms,))
            if self._active_page._timer_interval_ms > 0:
                js_to_browser.append("setTimeout(timer_tick, timer_interval_ms);")
        if self._active_page._static:
            js_to_browser.extend([
                "pending_server_event = 0;",
                "timer_interval_ms = 0;",
                'session_id = "";'])
        js_to_browser.append("document.getElementById('rootdiv').innerHTML=%r;" %
            (self._active_page.tokenized_html(),))
        self._add_to_browser_queue("".join(js_to_browser))

    def close(self):
        self._protocol.close_session(self._session_id)
        if self._delayed_response_conn:
            c, self._delayed_response_conn = self._delayed_response_conn, None
            _close(c)

    def _response_from_browser_queue(self, lock=True):
        if lock:
            self._to_browser_queue_lock.acquire()
        response = ';\n\n'.join(self._to_browser_queue)
        self._to_browser_queue = []
        if lock:
            self._to_browser_queue_lock.release()
        return response

    def _add_to_browser_queue(self, js):
        self._to_browser_queue_lock.acquire()
        try:
            self._to_browser_queue.append(js)
        finally: self._to_browser_queue_lock.release()
        if self._delayed_response_conn_lock.locked():
            # let the thread that received wait_server_event
            # continue immediately and send the browser queue
            self._delayed_response_conn_lock.release()

    def _handle_http_data(self, data):
        def check_event(data):
            """
            If something must be responded to the browser right away,
            it is returned as a return value. This should be done only
            when the browser requests the whole page. Those responses
            are in HTML. Normal responses (Javascript) is sent by
            putting the data in 'to_browser_queue'.
            """
            # parse event
            method_name = b""
            method_call = None
            try:
                # FIX: repeating code (check_session) --- implement
                # URL parsing in one place only.
                postline = data[:data.index(b"\n")].strip()
                first_slash = postline.index(b"/")
                second_slash = postline.index(b"/", first_slash + 1)
                session_id = postline[first_slash + 1:second_slash]
                method_call_raw = urllib.parse.unquote_to_bytes(postline[second_slash+1:postline.rfind(b" ")])
                method_name = method_call_raw[:method_call_raw.find(b"(")]
                if method_name == b"wait_server_event":
                    return "wait_server_event"
                elif method_name == b"timer_tick":
                    if not _re_timer_tick.match(method_call_raw):
                        raise ValueError('illegal timer_tick call %r' % (method_call_raw[:42].decode("utf-8"),))
                    else:
                        method_call = method_call_raw # passed security check: _re_timer_tick match
                elif not method_name in b"TC":
                    raise ValueError('invalid method name in %r' % (method_call_raw[:42].decode("utf-8"),))
                elif not method_call_raw in self._active_page._token2python:
                    raise ValueError('token %r not found in page' % (method_call_raw[:42].decode("utf-8"),))
                else:
                    method_call = self._active_page._token2python[method_call_raw]
                ctx_vars = json.loads(data[data.index(b'\r\n\r\n')+4:].strip())
            except Exception as e:
                log("Cannot parse event from data %r: %s" % (data.decode("utf-8"), e))
                return None
            method_env = {}
            method_env.update(self._active_page._env) # define callback functions in env
            ctx = Context(self, self._active_page)
            for var in ctx_vars:
                setattr(ctx, var, ctx_vars[var])
            method_env['ctx'] = ctx

            if method_name == b"":
                # matching page_id but request has no
                # parameters. Assume that browser reload has been pressed.
                # Response must be urgent, because the browser expects
                # to get all the page at once.
                _thread.start_new_thread(self._active_page.browser_reload, ())
                # TODO: send the base page and the html of the current form
                # *in the same package* to save time
                return None
            elif method_name == b"timer_tick" and not "timer_tick" in method_env:
                # skip calling timer_tick if there is no callback for it
                return 1
            elif method_name == b"C":
                # call current() callback
                try:
                    method_call(ctx_vars['current_dict'])
                except Exception as e:
                    log("http_server: exception when calling current() callback:\n    %s\n%s" % (e, traceback.format_exc()))
                return 1
            else:
                # evaluate untokenized method or validated timer_tick expression
                try:
                    eval(method_call, method_env, method_env)
                    return 1
                except Exception as e:
                    log("http_server: exception when evaluating %r:\n    %s\n%s" % (method_call, e, traceback.format_exc()))

        # The following lines should be executed reasonably
        # quickly in order to send response in time and thereby
        # avoid browser queueing ajax requests. Everything that
        # may take time should be done in a separate thread.

        # Check if this message is an event
        parsed_event = check_event(data)

        if not parsed_event:
            log("http_server: could not handle message, closing")
            return None
        if parsed_event == "wait_server_event":
            return "wait_server_event"
        return self._response_from_browser_queue()

class Page(object):
    counter = -1 # the first instance will be "dummy", not worth of a natural number
    def __init__(self, session, html, **kw):
        """takes html and session object (parent) as arguments"""
        self._session = session
        self._html = html
        self._token2python = {}
        self._python2token = {}
        self._tokenized_html = self._tokenize_html(html)
        self._elements_received = 0
        self.name = str(Page.counter)
        self._env = {}
        self._timer_interval_ms = kw.get("timer_interval_ms", None)
        self._pending_server_event = kw.get("pending_server_event", None)
        self._static = kw.get("static", None)
        Page.counter += 1

    def _tokenize_html(self, html):
        # adds tokens to local tokens, returns tokenized html
        tokenized_html = []
        whats_left = html
        python_event_match = _re_python_attr.search(whats_left)
        while python_event_match:
            tokenized_html.append(whats_left[:python_event_match.start()])
            python_code = python_event_match.groupdict()['python']
            js_event = python_event_match.groupdict()['js_event']
            if not python_event_match.groupdict()['event_attrs'] is None:
                event_attrs = str([a.strip() for a in python_event_match.groupdict()['event_attrs'].split(",")])
            else:
                event_attrs = "undefined"
            if python_code in self._python2token:
                token = self._python2token[python_code]
            else:
                token = b"T(%d)" % (len(self._python2token),)
                self._token2python[token] = python_code
                self._python2token[python_code] = token
            tokenized_html.append(''' %s="send_event('%s', event, this, %s)"''' % (js_event, token.decode("utf-8"), event_attrs))
            whats_left = whats_left[python_event_match.end():]
            python_event_match = _re_python_attr.search(whats_left)
        tokenized_html.append(whats_left)
        return "".join(tokenized_html)

    def html(self):
        return self._html

    def tokenized_html(self):
        return self._tokenized_html

    def update_env(self, env_dict):
        """add variables (keys) and values (values) in dict to run env"""
        self._env.update(env_dict)
        for key in sorted(env_dict.keys()):
            if key.startswith("python-on"):
                # this is not variable name to eval environment,
                # this is a global callback. set it as window listener
                if "(" in key and ")" in key: # there is event attr list
                    key_nofilter, _after_open_paren = key.split("(", 1)
                    env_dict[key_nofilter] = env_dict[key]
                    del env_dict[key]
                    key = key_nofilter
                    _in_paren = _after_open_paren.split(")", 1)[0]
                    event_attrs = [a.strip() for a in _in_paren.split(",")]
                    event_attr_list = str(event_attrs)
                else:
                    event_attr_list = "undefined"
                try:
                    js_event = _re_python_event.match(key).groupdict()['js_event'][2:] # skip "on" prefix
                except Exception as e:
                    raise ValueError('invalid python-on* event: %r' % (key,))
                python_code = env_dict[key]
                self._tokenize_html('<dontcare %s="%s" />' % (key, python_code))
                token = self._python2token[python_code]
                self._session._add_to_browser_queue(
                    "window.addEventListener(%r, function (event) { send_event(%r, event, undefined, %s); })" % (js_event, token.decode("utf-8"), event_attr_list))

    def session(self):
        return self._session

    def env(self):
        return self._env

    def current(self, names, cb):
        """Get current page contents

        Parameters:
          names (list of strings):
                  strings in the list are either:
                  1. element_ids (returns inner_html)
                  2. element_id.attribute_name (returns attribute value)

          cb (function that takes dict as a parameter):
                  once current contents are received from the browser,
                  cb is called with a dict
                      {name: inner_html_or_attr_value}
                  as a parameter

        Returns:
          None

        Examples:
          page.current(["my-text-input.value", "mytextarea"],
                       lambda d: pprint.pprint(d))
        """
        token = b"C(%r)" % (",".join(names),)
        to_queue = ['send_to_server(%(token)r, JSON.stringify({"current_dict":{' % {"token": token.decode("UTF-8")}]
        for name in names:
            if "." in name:
                eid, attr = name.split(".", 1)
            else:
                eid, attr = name, "innerHTML"
            to_queue.append('%(name)r: document.getElementById(%(eid)r).%(attr)s,' % {
                'name': name,
                'eid': eid,
                'attr': attr})
        to_queue.append('}}), eval_response)')
        self._token2python[token] = cb
        self._session._add_to_browser_queue(''.join(to_queue))

    def update(self, name_content_dict):
        """Change page contents: inner HTMLs or attributes

        Parameters:
          name_content_dict (dict):
                  dictionary of keys and values of either or both:
                  1. element_id: inner_html
                  2. element_id.attribute_name: new_attribute_value
                  3. "js": javascript_to_be_executed

        Examples: replace OLD with NEW...
          1. in <ELEMENT id="EID">OLD</ELEMENT>
            page.update({'EID': 'NEW'})
          2. in <ELEMENT id="EID" ATTR="OLD">DATA</ELEMENT>
            page.update({'EID.ATTR': 'NEW'})
        """
        if not isinstance(name_content_dict, dict):
            raise TypeError('Page.update() requires dict as a parameter, got %s'
                            % (type(name_content_dict),))
        to_queue = []
        for name in name_content_dict:
            if name == "js":
                # run raw javascript
                to_queue.append(name_content_dict[name])
            elif name.startswith("window."):
                # direct access to some javascript objects
                # example: {"window.location.href": "http://new/url"}
                to_queue.append("%(eid)s=%(new_value)r;" % (name, name_content_dict[name]))
            elif "." in name:
                # replace an attribute
                # example: {"myEltID.myEltAttr": "new value"}
                eid, attr = name.split(".", 1)
                if not "-" in attr and not " " in attr:
                    to_queue.append("document.getElementById(%(eid)r).%(attr)s=%(new_value)r;" % {
                        'eid': eid,
                        'attr': attr,
                        'new_value': name_content_dict[name]})
                else:
                    to_queue.append("document.getElementById(%(eid)r).setAttribute(%(attr)r, %(new_value)r);" % {
                        'eid': eid,
                        'attr': attr,
                        'new_value': name_content_dict[name]})
            else:
                # replace contents of element
                # example: {"myDivID": "new html"}
                content = self._tokenize_html(name_content_dict[name])
                to_queue.append("document.getElementById(%(name)r).innerHTML=%(content)r;" % {
                    'name': name,
                    'content': content})
        self._session._add_to_browser_queue("".join(to_queue))

    def browser_reload(self):
        """Reload-button pressed"""
        pass

class Context(object):
    def __init__(self, session, page):
        self.session = session
        self.page = page

_protocol = Protocol()
new_session = _protocol.new_session

if __name__ == "__main__":
    print("httpgui self-test and example")
    import queue
    import sys
    def log(msg):
        sys.stderr.write('log: %s\n' % (msg,))
    q = queue.Queue()
    def close(ctx):
        p = ctx.session.new_page("thank you", static=True)
        time.sleep(1)
        ctx.session.close()
        q.put("x")
    def timer_tick(ctx, count):
        ctx.page.update({'timer': str(count), # set innerHTML of id=timer element
                         'timer.style': 'color: %s;' % (["red", "green", "blue"][count % 3],)}) # set style attribute of id=timer element
    session = new_session("localhost:54321")
    p = session.new_page('<p python-onclick="close(ctx)">click close</p>'
                         '<p id="timer">no ticks yet</p>',
                         close,
                         timer_tick,
                         timer_interval_ms=500)
    q.get() # wait until close is clicked
