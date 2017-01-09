#!/usr/bin/python3
"""
Help Documentation Browser
"""
import os
import sys

import cairo

import yutani
import toaru_fonts
import text_region

class HelpBrowserWindow(yutani.Window):

    base_width = 800
    base_height = 600

    def __init__(self, decorator):
        super(HelpBrowserWindow, self).__init__(self.base_width + decorator.width(), self.base_height + decorator.height(), title="Help Browser", icon="help", doublebuffer=True)
        self.move(100,100)
        self.decorator = decorator
        self.last_topic = None
        self.current_topic = "0_index.trt"
        self.text_buffer = None
        self.text_offset = 0
        self.scroll_offset = 0
        self.tr = None
        self.size_changed = False
        self.update_text_buffer()

        self.special = {}
        self.special['contents'] = self.special_contents
        self.special['demo'] = self.special_demo

    def get_title(self, document):
        if document.startswith("special:"):
            if self.current_topic[8:] in self.special:
                return self.special[self.current_topic[8:]].__doc__
            return "???"
        path = f'/usr/share/help/{document}'
        if not os.path.exists(path):
            return "(file not found)"
        with open(path,'r') as f:
            lines = f.readlines()
            for x in lines:
                x = x.strip()
                if x.startswith('<h1>') and x.endswith('</h1>'):
                    return x[4:-5]
            return document.replace('.trt','').title()

    def special_contents(self):
        """Table of Contents"""
        # List all things.
        output = "\n<h1>Table of Contents</h1>\n\nThis table of contents is automatically generated.\n\n"
        output += "<h2>Special Pages</h2>\n\n"
        for k in self.special:
            output += f"➤ <link target=\"special:{k}\">{self.special[k].__doc__}</link>\n"
        output += "\n<h2>Documentation</h2>\n\n"
        for k in sorted(os.listdir('/usr/share/help')):
            if k.endswith('.trt'):
                output += f"➤ <link target=\"{k}\">{self.get_title(k)}</link>\n"
        for directory,_,files in os.walk('/usr/share/help'):
            if directory == '/usr/share/help':
                continue
            files = sorted([x for x in files if not x.startswith('.')])
            if files:
                d = directory.replace('/usr/share/help/','')
                output += "\n<h3>" + d.title() + "</h3>\n\n"
                for k in files:
                    k = d + '/' + k
                    output += f"➤ <link target=\"{k}\">{self.get_title(k)}</link>\n"
        return output

    def special_demo(self):
        """Formatting demo"""
        return f"""

<h1>This is a big header</h1>
This is text below that.
<h2>This is a medium header</h2>

<h3>This is a small header</h3>

This is normal text. <b>This is bold text.</b> <i>This is italic text.</i> <b><i>This is both.</i></b>
<link target=\"0_index.trt\">go home</link>"""

    def get_document_text(self):
        if self.current_topic.startswith("special:"):
            if self.current_topic[8:] in self.special:
                return self.special[self.current_topic[8:]]()
        else:
            path = f'/usr/share/help/{self.current_topic}'
            if os.path.exists(path):
                with open(path,'r') as f:
                    return f.read()
        return f"""<b>Document Not Found</b>

Uh oh, looks like the help document you tried to open ({self.current_topic}) wasn't available. Do you want to <link target=\"{self.last_topic}\">go back</link> or <link target=\"0_index.trt\">return to the index</link>?

You can also <link target=\"special:contents\">check the Table of Contents</link>.

"""

    def get_help_text(self):
        output  = f"<b><link target=\"{self.last_topic}\">Back</link>"
        output += f" | <link target=\"0_index.trt\">Home</link>"
        output += f" | <link target=\"special:contents\">Contents</link>"
        output += f" | <i>{self.current_topic}</i>: {self.get_title(self.current_topic)}"
        output += f"</b>\n"
        output += self.get_document_text() + "\n\n" + output
        return output

    def navigate(self, target):
        self.last_topic = self.current_topic
        self.current_topic = target
        self.text_offset = 0
        self.scroll_offset = 0
        self.tr.set_richtext(self.get_help_text())
        self.update_text_buffer()

    def update_text_buffer(self):
        if self.text_buffer:
            self.text_buffer.destroy()

        self.text_buffer = yutani.GraphicsBuffer(self.width - self.decorator.width(),self.height-self.decorator.height()+80)
        surface = self.text_buffer.get_cairo_surface()
        ctx = cairo.Context(surface)
        ctx.rectangle(0,0,surface.get_width(),surface.get_height())
        ctx.set_source_rgb(1,1,1)
        ctx.fill()

        pad = 10
        if not self.tr:
            self.tr = text_region.TextRegion(pad,0,surface.get_width()-pad*2,surface.get_height())
            self.tr.set_line_height(18)
            self.tr.set_richtext(self.get_help_text())
        elif self.size_changed:
            self.size_changed = False
            self.tr.resize(surface.get_width()-pad*2,surface.get_height()-pad*2)

        self.tr.scroll = self.scroll_offset
        self.tr.draw(self.text_buffer)

    def draw(self):
        surface = self.get_cairo_surface()

        WIDTH, HEIGHT = self.width - self.decorator.width(), self.height - self.decorator.height()

        ctx = cairo.Context(surface)
        ctx.translate(self.decorator.left_width(), self.decorator.top_height())
        ctx.rectangle(0,0,WIDTH,HEIGHT)
        ctx.set_source_rgb(204/255,204/255,204/255)
        ctx.fill()

        text = self.text_buffer.get_cairo_surface()
        ctx.set_source_surface(text,0,-self.text_offset)
        ctx.paint()

        self.decorator.render(self)

    def finish_resize(self, msg):
        """Accept a resize."""
        self.resize_accept(msg.width, msg.height)
        self.reinit()
        self.size_changed = True
        self.update_text_buffer()
        self.draw()
        self.resize_done()
        self.flip()

    def scroll(self, amount):
        self.text_offset += amount
        while self.text_offset < 0:
            if self.scroll_offset == 0:
                self.text_offset = 0
            else:
                self.scroll_offset -= 1
                self.text_offset += self.tr.line_height
        while self.text_offset >= self.tr.line_height:
            self.scroll_offset += 1
            self.text_offset -= self.tr.line_height
        self.update_text_buffer()

    def mouse_event(self, msg):
        if d.handle_event(msg) == yutani.Decor.EVENT_CLOSE:
            window.close()
            sys.exit(0)
        if msg.command == yutani.MouseEvent.CLICK:
            e = self.tr.click(msg.new_x-self.decorator.left_width(),msg.new_y-self.decorator.top_height()+self.text_offset)
            if e and 'link' in e.extra:
                self.navigate(e.extra['link'])
                return True
        if msg.buttons & yutani.MouseButton.SCROLL_UP:
            self.scroll(-30)
            return True
        elif msg.buttons & yutani.MouseButton.SCROLL_DOWN:
            self.scroll(30)
            return True
        return False

    def keyboard_event(self, msg):
        if msg.event.action != 0x01:
            return False # Ignore anything that isn't a key down.
        if msg.event.keycode == yutani.Keycode.HOME:
            self.text_offset = 0
            self.scroll_offset = 0
            self.update_text_buffer()
            return True
        elif msg.event.keycode == yutani.Keycode.PAGE_UP:
            self.scroll(int(-self.height/2))
            return True
        elif msg.event.keycode == yutani.Keycode.PAGE_DOWN:
            self.scroll(int(self.height/2))
            return True
        elif msg.event.key == b"q":
            self.close()
            sys.exit(0)

if __name__ == '__main__':
    yutani.Yutani()
    d = yutani.Decor()

    window = HelpBrowserWindow(d)

    if len(sys.argv) > 1:
        window.navigate(sys.argv[-1])

    window.draw()
    window.flip()

    while 1:
        # Poll for events.
        msg = yutani.yutani_ctx.poll()
        if msg.type == yutani.Message.MSG_SESSION_END:
            window.close()
            break
        elif msg.type == yutani.Message.MSG_KEY_EVENT:
            if msg.wid == window.wid:
                if window.keyboard_event(msg):
                    window.draw()
                    window.flip()
        elif msg.type == yutani.Message.MSG_WINDOW_FOCUS_CHANGE:
            if msg.wid == window.wid:
                window.focused = msg.focused
                window.draw()
                window.flip()
        elif msg.type == yutani.Message.MSG_RESIZE_OFFER:
            window.finish_resize(msg)
        elif msg.type == yutani.Message.MSG_WINDOW_MOUSE_EVENT:
            if msg.wid == window.wid:
                if window.mouse_event(msg):
                    window.draw()
                    window.flip()


