import html
import sys
import _thread
import time

import httpgui
httpgui.log = lambda msg: sys.stderr.write(msg + "\n")

html_chat_room = """
<style>
.t{font: 14px sans-serif; fill: black;}
.e{font: bold 14px sans-serif; fill: blue;}
</style>
<table>
<tr><td>Server:</td><td id="time"></td></tr>
<tr><td>Room:</td><td id="room">%(room)s <input id="destroy" type="button" value="Destroy" python-onclick="onclick_destroy(ctx)"/></td></tr>
<tr><td>Users:</td><td id="users"></td></tr>
</table>
<div id="messages">
%(messages)s
</div>
%(user)s: <input id="message" type="text" class="t"/>
<input id="send" type="button" value="Send" python-onclick()="onclick_send(ctx)"/>
<input id="up" type="button" value="&uarr;" python-onclick()="onclick_up(ctx)"/>
<input id="down" type="button" value="&darr;" python-onclick()="onclick_down(ctx)"/>
"""

html_bad_url = """Bad URL. Better luck next time."""

html_room_destroyed = """Room destroyed."""

class Room_user:
    session = None
    messages = None
    typed_last = 0
    typing = False
    editing_message = None

max_messages = 16
message_height = 15
room_user = {} # {room: {user: Room_user}}

def error(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

def check_who_stopped_typing():
    while True:
        time.sleep(1)
        t = time.time()
        for room in room_user:
            for user in room_user[room]:
                u = room_user[room][user]
                if u.typing == True and t - u.typed_last > 2:
                        u.typing = False
            update_users(room)

def onkeydown(ctx):
    room, user = ctx.session.room, ctx.session.user
    u = room_user[room][user]
    if ctx.event["key"] == "Enter":
        # Send message
        ctx.page.current(['message.value'],
                         lambda d: send_message(ctx.session, d['message.value']))
        u.typing = False
        u.typed_last = 0
        update_users(room)
    elif len(ctx.event["key"]) == 1: # letter, number
        u.typed_last = time.time()
        if not u.typing:
            u.typing = True
            update_users(room)
    elif ctx.event["key"] == "ArrowUp":
        onclick_up(ctx)
    elif ctx.event["key"] == "ArrowDown":
        onclick_down(ctx)

def update_editing_message(room, user):
    u = room_user[room][user]
    if not u.editing_message is None:
        msg = u.messages[u.editing_message].split(": ", 1)[-1]
        u.session.page().update({'message.value': html.unescape(msg)})
    else:
        u.session.page().update({'message.value': ''})
    update_messages(room, user, None)

def onclick_up(ctx):
    room, user = ctx.session.room, ctx.session.user
    u = room_user[room][user]
    if u.editing_message is None:
        u.editing_message = 0
    else:
        if u.editing_message + 1 < len(u.messages):
            u.editing_message += 1
    update_editing_message(room, user)

def onclick_down(ctx):
    room, user = ctx.session.room, ctx.session.user
    u = room_user[room][user]
    if not u.editing_message is None:
        u.editing_message -= 1
        if u.editing_message < 0:
            u.editing_message = None
        update_editing_message(room, user)

def onclick_send(ctx):
    ctx.page.current(['message.value'],
                     lambda d: send_message(ctx.session, d['message.value']))

def onclick_destroy(ctx):
    room = ctx.session.room
    for user in room_user[room]:
        room_user[room][user].session.new_page(html_room_destroyed, static=True)
    del room_user[room]

def messages_to_html(room, user, animate):
    u = room_user[room][user]
    html = ['''
    <svg height="%d" width="480">
    ''' % (max_messages * message_height,)]
    for m_index, m in enumerate(room_user[room][user].messages):
        end_y = (max_messages - m_index - 1) * message_height
        start_y = end_y
        if m_index != u.editing_message:
            text_class = "t"
        else:
            text_class = "e"
        if animate == "scroll 1 up":
            start_y = (max_messages - m_index) * message_height
            animation = '<animate attributeName="y" from="%d" to="%d" dur="1s" fill="freeze"/>' % (start_y, end_y)
        elif isinstance(animate, str) and animate.startswith("shake") and m_index == int(animate.split()[1]):
            animation = '<animate attributeName="x" values="2;0;4;1;2;0;1;0" dur="0.7s"/>'
        else:
            animation = ""
        html.append('<text x="0" y="%d" class="%s">%s%s</text>' % (start_y, text_class, animation, m))
    html.append('</svg>')
    return "\n".join(html)

def update_messages(room, user, animate):
    room_user[room][user].session.page().update({'messages': messages_to_html(room, user, animate)})

def send_message(session, message):
    message = html.escape(message)
    room, sender = session.room, session.user
    u = room_user[room][sender]
    if not u.editing_message is None:
        # modify existing message
        orig_message = u.messages[u.editing_message]
        for user in room_user[room]:
            try:
                edit_index = room_user[room][user].messages.index(orig_message)
            except ValueError:
                continue # this user never received edited message
            room_user[room][user].messages[edit_index] = sender + ": " + message
            u.editing_message = None
            update_messages(room, user, "shake " + str(edit_index))
    else:
        # add new message to all
        for user in room_user[room]:
            room_user[room][user].messages = ([sender + ": " + message] + room_user[room][user].messages)[:max_messages]
            update_messages(room, user, "scroll 1 up")
    session.page().update({'message.value': ''})

def update_users(room):
    users = []
    for user in sorted(room_user[room]):
        if room_user[room][user].typing:
            users.append("<b>" + user + "</b>")
        else:
            users.append(user)
    html_users = ", ".join(users)
    for user in room_user[room]:
        room_user[room][user].session.page().update(
            {'users': html_users,
             'time': time.strftime(" %H:%M:%S")})

if __name__ == "__main__":
    try:
        host_port = sys.argv[1]
    except:
        error('Usage: chat HOST:PORT\nExample: chat 0.0.0.0:5555')
    _thread.start_new_thread(check_who_stopped_typing, ())
    while 1:
        session = httpgui.new_session(host_port, env=globals())
        try:
            _, room, user = session.path().split("/")
            if room == "" or user == "":
                raise
        except:
            session.new_page(html_bad_url, static=True)
            continue
        session.room = room
        session.user = user
        if not room in room_user:
            room_user[room] = {}
        room_user[room][user] = Room_user() # todo: delete old?
        room_user[room][user].session = session
        room_user[room][user].messages = ['entered room ' + room] + ['' * (max_messages - 1)]
        session.new_page(html_chat_room %
                         {'room': room,
                          'user': user,
                          'messages': messages_to_html(room, user, "scroll 1 up")},
                         {'python-onkeydown(key)': "onkeydown(ctx)"})
        update_users(room)
