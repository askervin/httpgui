"""html-inputs.py - html input element example

Usage: python3 html-inputs.py BINDHOST:PORT

Example: python3 html-inputs.py 0.0.0.0:5555
"""
import html
import pprint
import sys
import time

import httpgui
httpgui.log = lambda msg: sys.stderr.write(msg + "\n")

def error(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

def keydown(ctx):
    try:
        key = str(ctx.event['key'])
        if len(key) == 1:
            ctx.session.typed.append(key)
        elif key == "Backspace":
            ctx.session.typed.pop()
        elif key == "Enter":
            ctx.session.typed.append("\n")
        else:
            print("key: %r" % (key,))
        ctx.page.update({
            'typed-text': html.escape("".join(ctx.session.typed))
        })
    except Exception as e:
        print("error in handing browser keypress:", e)

def clicked(ctx):
    pprint.pprint({'id': ctx.event['target']['id'],
                   'value': ctx.event['target']['value']})

def get_values(ctx):
    ctx.page.current(
        ['my-checkbox.checked',
         'my-color.value',
         'my-date.value',
         'my-datetime-local.value',
         'my-email.value',
         'my-file.value',
         'my-month.value',
         'my-number.value',
         'my-password.value',
         'my-radio0.checked',
         'my-radio1.checked',
         'my-range.value',
         'my-search.value',
         'my-tel.value',
         'my-text.value',
         'my-time.value',
         'my-url.value',
         'my-week.value',
         'my-textarea.value'],
        lambda d: pprint.pprint(d))

if __name__ == "__main__":
    try:
        host_port = sys.argv[1]
    except:
        error('Usage: html-inputs BINDHOST:PORT\nExample: html-inputs 0.0.0.0:5555')
    while 1:
        session = httpgui.new_session(host_port, env=globals())
        session.typed = [] # add here typed characters
        session.new_page('''
        <h1>HTML input elements</h1>
        <p>Captured onkeydown: <pre id="typed-text"></pre></p>
        <form>
        Button: <input id="my-button" type="button" value="my button text" %(click)s /> <br />
        Checkbox: <input id="my-checkbox" type="checkbox" %(click)s /> <br />
        Color: <input id="my-color" type="color" %(click)s /> <br />
        Date: <input id="my-date" type="date" %(click)s /> <br />
        Datetime-local: <input id="my-datetime-local" type="datetime-local" %(click)s /> <br />
        Email: <input id="my-email" type="email" %(click)s /> <br />
        File: <input id="my-file" type="file" %(click)s /> <br />
        Hidden: <input id="my-hidden" type="hidden" %(click)s /> <br />
        Image: <input id="my-image" type="image" %(click)s /> <br />
        Month: <input id="my-month" type="month" %(click)s /> <br />
        Number: <input id="my-number" type="number" %(click)s /> <br />
        Password: <input id="my-password" type="password" %(click)s /> <br />
        Radio: <input id="my-radio0" type="radio" name="my-radio" value="one" %(click)s /> 1
               <input id="my-radio1" type="radio" name="my-radio" value="two" %(click)s /> 2 <br />

        Range: <input id="my-range" type="range" min="0" max="42" value="40" %(click)s /> <br />
        Reset: <input id="my-reset" type="reset" %(click)s /> <br />
        Search: <input id="my-search" type="search" %(click)s /> <br />
        Submit: <input id="my-submit" type="submit" %(click)s /> <br />
        Tel: <input id="my-tel" type="tel" %(click)s /> <br />
        Text: <input id="my-text" type="text" %(click)s /> <br />
        Time: <input id="my-time" type="time" %(click)s /> <br />
        Url: <input id="my-url" type="url" %(click)s /> <br />
        Week: <input id="my-week" type="week" %(click)s /> <br />
        </form>
        Textarea: <textarea id="my-textarea">type here...</textarea> <br />
        <input type="button" value="fetch all values from the page" python-onclick="get_values(ctx)" />
        ''' % {'click': 'python-onclick="clicked(ctx)"'},
                         {'python-onkeydown': 'keydown(ctx)'})
