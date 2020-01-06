import html
import sys

import httpgui
httpgui.log = lambda msg: sys.stderr.write(msg + "\n")

html_chat_room = """
<table>
<tr><td>Room:</td><td id="room">%(room)s <input id="destroy" type="button" value="Destroy" python-onclick="onclick_destroy(ctx)"/></td></tr>
<tr><td>Users:</td><td id="users"></td></tr>
</table>
<div id="messages">
%(messages)s
</div>
<input id="message" type="text"/><input id="send" type="button" value="Send" python-onclick="onclick_send(ctx)"/>
"""

html_bad_url = """Bad URL. Better luck next time."""

html_room_destroyed = """Room destroyed."""

class Room_user:
    session = None
    messages = None

max_messages = 16
message_height = 15
room_user = {} # {room: {user: Room_user}}

def error(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

def onclick_send(ctx):
    ctx.page.current(['message.value'],
                     lambda d: send_message(ctx.session, d['message.value']))

def onclick_destroy(ctx):
    room = ctx.session.room
    for user in room_user[room]:
        room_user[room][user].session.new_page(html_room_destroyed, static=True)
    del room_user[room]

def messages_to_html(room, user):
    html = ['<svg height="%d" width="480">' % (max_messages * message_height,)]
    for m_index, m in enumerate(room_user[room][user].messages):
        start_y = (max_messages - m_index) * message_height
        end_y = (max_messages - m_index - 1) * message_height
        html.append('<text x="0" y="%d" style="fill:black;"><animate attributeName="y" from="%d" to="%d" dur="1s" fill="freeze"/>%s</text>' % (start_y, start_y, end_y, m))
    html.append('</svg>')
    return "\n".join(html)

def send_message(session, message):
    message = html.escape(message)
    if "python-onclick" in message:
        message = message.replace('python-onclick', 'python--onclick')
    room = session.room
    for user in room_user[room]:
        room_user[room][user].messages = ([session.user + ": " + message] + room_user[room][user].messages)[:max_messages]
        room_user[room][user].session.page().update({'messages': messages_to_html(room, user)})
    session.page().update({'message.value': ''})

def user_joined(room):
    for user in room_user[room]:
        other_room_users = ", ".join([u for u in sorted(room_user[room].keys()) if u != user])
        if other_room_users:
            other_room_users = ", " + other_room_users
        this_room_users = "<strong>" + user + "</strong>" + other_room_users
        room_user[room][user].session.page().update({'users': this_room_users})

if __name__ == "__main__":
    try:
        host_port = sys.argv[1]
    except:
        error('Usage: chat HOST:PORT\nExample: chat 0.0.0.0:5555')
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
        session.new_page(html_chat_room % {'room': room, 'messages': messages_to_html(room, user)})
        user_joined(room)
