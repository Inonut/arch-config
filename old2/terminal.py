import urwid

def main():
    urwid.set_encoding('utf8')
    term = urwid.Terminal(['/usr/bin/cfdisk'], )
    edit = urwid.Edit('focus test edit: ')

    mainframe = urwid.LineBox(
        urwid.Pile([
            ('weight', 70, term),
            ('fixed', 1, urwid.Filler(edit)),
        ]),
    )

    def set_title(widget, title):
        mainframe.set_title(title)

    def quit(*args, **kwargs):
        raise urwid.ExitMainLoop()

    def handle_key(key):
        if key in ('q', 'Q'):
            quit()
        edit.set_edit_text = key

    urwid.connect_signal(term, 'title', set_title)
    urwid.connect_signal(term, 'closed', quit)

    loop = urwid.MainLoop(
        mainframe,
        handle_mouse=False,
        unhandled_input=handle_key)

    term.main_loop = loop

    loop.run()

if __name__ == '__main__':
    main()