import enum
import shlex
import subprocess
import typing
import parted
import urwid


class PartitionLabel(enum.Enum):
    GPT = ('GPT Partition', 'New and better')
    MRB = ('MRB Partition', 'Old and good')


class PartitionModel(object):

    def __init__(self,
                 label: PartitionLabel = PartitionLabel.GPT,
                 root: str = None,
                 swap: str = None,
                 boot: str = None,
                 committed: bool = False,
                 ) -> None:
        self.committed = committed
        self.boot = boot
        self.swap = swap
        self.root = root
        self.label = label

    def __str__(self) -> str:
        return """
label = {}
root = {}
swap = {}
boot = {}
committed = {}
""".format(self.label, self.root, self.swap, self.boot, self.committed)


def raise_(ex):
    raise ex


class PartitionTable(urwid.Frame):

    def __init__(self,
                 onOk=lambda result: raise_(urwid.ExitMainLoop()),
                 onCancel=lambda: raise_(urwid.ExitMainLoop())
                 ):

        self.isCommitted = False
        self.onOk = onOk
        self.onCancel = onCancel
        self.partitionLabelGroup = []

        self.labelList = urwid.SimpleListWalker([
            urwid.RadioButton(self.partitionLabelGroup, PartitionLabel.GPT.value[0]),
            urwid.RadioButton(self.partitionLabelGroup, PartitionLabel.MRB.value[0]),
        ])
        self.deviceList = urwid.SimpleListWalker([
            urwid.Button(device.path, on_press=self.replaceDevice, user_data=device.path) for device in
            self.currentDevices()
        ])
        self.description = urwid.Text('')
        self.instructions = urwid.Text('')
        self.bootText = urwid.Edit('')
        self.swapText = urwid.Edit('')
        self.rootText = urwid.Edit('')

        self.detailBox = urwid.LineBox(
            title='Details',
            original_widget=urwid.Filler(
                valign=urwid.TOP,
                body=urwid.Pile([
                    urwid.AttrMap(self.instructions, 'reversed'),
                    self.description
                ])
            )
        )
        self.partitionLabelBox = urwid.LineBox(
            title='Partition Label',
            original_widget=urwid.ListBox(self.labelList)
        )
        self.deviceBox = urwid.LineBox(
            title='Found devices',
            original_widget=urwid.ListBox(self.deviceList)
        )
        self.partitionDetailBox = urwid.LineBox(
            title='What actually need',
            original_widget=urwid.ListBox(urwid.SimpleListWalker([
                urwid.Columns([
                    (7, urwid.Text('Boot:')),
                    self.bootText
                ]),
                urwid.Columns([
                    (7, urwid.Text('Swap:')),
                    self.swapText
                ]),
                urwid.Columns([
                    (7, urwid.Text('Root:')),
                    self.rootText
                ]),
            ]))
        )

        body = urwid.Pile([
            self.detailBox,
            urwid.Columns([
                (30, self.partitionLabelBox),
                urwid.LineBox(
                    title='Partition Devices',
                    original_widget=urwid.Columns([
                        self.deviceBox,
                        self.partitionDetailBox,
                    ])
                ),
            ])
        ])

        footer = urwid.Columns([
            urwid.AttrMap(urwid.Text('Use tab to arrive here -->>>'), 'help'),
            urwid.GridFlow([
                urwid.Button('Ok', on_press=self._commit),
                urwid.Button('Cancel', on_press=self._rollback),
            ], 10, 3, 3, urwid.RIGHT)
        ])

        super().__init__(body, footer=footer)

        urwid.connect_signal(self.labelList, 'modified', self.updatePartitionLabelDetails)
        urwid.connect_signal(self.deviceList, 'modified', self.updatePartitionDeviceDetails)
        self.updatePartitionLabelDetails()

    def replaceDevice(self, btn, path):
        # self.description.set_text(path + '1')
        prefix = ''
        if path[-1].isdigit():
            prefix = 'p'
        self.bootText.set_edit_text(path + prefix + '1')
        self.swapText.set_edit_text(path + prefix + '2')
        self.rootText.set_edit_text(path + prefix + '3')

    def processResult(self) -> PartitionModel:
        result = PartitionModel()
        result.committed = self.isCommitted

        for o in self.partitionLabelGroup:
            if o.get_state() is True:
                if PartitionLabel.GPT.value[0] == o.get_label():
                    result.label = PartitionLabel.GPT.name
                elif PartitionLabel.MRB.value[0] == o.get_label():
                    result.label = PartitionLabel.MRB.name

        result.boot = self.bootText.get_text()[0]
        result.swap = self.swapText.get_text()[0]
        result.root = self.rootText.get_text()[0]

        return result

    def _commit(self, item):
        self.isCommitted = True
        self.onOk(self.processResult())

    def _rollback(self, item):
        self.isCommitted = False
        self.onCancel()

    def currentDevices(self) -> typing.List[parted.Device]:
        return parted.getAllDevices()

    def deviceInformation(self, path: str):
        cmd = 'fdisk -l {}'.format(path)

        return '\n'.join(subprocess.check_output(shlex.split(cmd)).decode("utf-8").split('\n'))

    def updatePartitionLabelDetails(self):
        self.instructions.set_text('Use UP/DOWN to move, SPACE/ENTER to select')
        if self.labelList.get_focus()[0].label == PartitionLabel.GPT.value[0]:
            self.description.set_text(PartitionLabel.GPT.value[1])
        elif self.labelList.get_focus()[0].label == PartitionLabel.MRB.value[0]:
            self.description.set_text(PartitionLabel.MRB.value[1])

    def updatePartitionDeviceDetails(self):
        self.instructions.set_text('Use UP/DOWN to move, ENTER to select')
        self.description.set_text(self.deviceInformation(self.deviceList.get_focus()[0].label))

    def keypress(self, size, key):
        if key == 'tab':
            if self.focus_part == 'body':
                self.set_focus('footer')
            elif self.focus_part == 'footer':
                self.set_focus('body')

        if key == 'right' and self.partitionLabelBox in self.get_focus_widgets():
            self.updatePartitionDeviceDetails()

        if key == 'left' and self.deviceBox in self.get_focus_widgets():
            self.updatePartitionLabelDetails()

        if key == 'left' and self.partitionDetailBox in self.get_focus_widgets():
            self.updatePartitionDeviceDetails()

        if key == 'right' and self.deviceBox in self.get_focus_widgets():
            self.instructions.set_text('Use UP/DOWN to move, can be editable, !!! BE CAREFUL !!!')

        return super().keypress(size, key)



class BoxButton(urwid.WidgetWrap):
    signals = ["click"]

    def __init__(self, label, on_press=None, user_data=None, attr_map='button', focus_map='highlight'):

        self._user_data = user_data

        self._label = urwid.Text(label, align=urwid.CENTER)

        w = urwid.AttrMap(
            w=urwid.LineBox(self._label),
            attr_map=attr_map,
            focus_map=focus_map)

        super().__init__(w)

        if on_press:
            urwid.connect_signal(self, 'click', on_press, self._user_data)

    def set_label(self, label):
        self._label.set_text(label)

    def get_label(self):
        return self._label.text

    def getUserData(self):
        return self._user_data

    def selectable(self):
        return True

    def keypress(self, size, key):
        if self._command_map[key] != urwid.ACTIVATE:
            return key

        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        if button != 1 or not urwid.util.is_mouse_press(event):
            return False

        self._emit('click')
        return True


class BoxPicker(urwid.WidgetPlaceholder):
    signals = ["click"]

    def __init__(self, label, choices=[""], attr_map='button', focus_map='highlight'):

        self._selected_index = None
        self.choices = choices

        self._label = urwid.Text(label, align=urwid.CENTER)
        self.line_box_widget = urwid.LineBox(
            original_widget=urwid.WidgetPlaceholder(self._label),
            title_align=urwid.LEFT
        )

        w = urwid.AttrMap(
            w=self.line_box_widget,
            attr_map=attr_map,
            focus_map=focus_map)

        super().__init__(w)

        urwid.connect_signal(self, 'click', lambda el: self.show_choices())

        self.show_on_selection_display()

    def show_choices(self):
        self.line_box_widget.set_title(self.get_label())

        self.line_box_widget.original_widget.original_widget = urwid.Text(self.choices[self._selected_index])

    def show_on_selection_display(self):
        self.line_box_widget.set_title("")

        self.line_box_widget.original_widget.original_widget = urwid.Columns(
            widget_list=[
                self._label,
                (1, urwid.Text('▼', urwid.RIGHT))
            ],
            dividechars=2
        )

    def set_label(self, label):
        self._label.set_text(label)

    def get_label(self):
        return self._label.text

    def get_selected_index(self):
        return self._selected_index

    def get_selected_value(self):
        return self.choices[self._selected_index]

    def selectable(self):
        return True

    def keypress(self, size, key):
        if self._selected_index is None:
            self._selected_index = 0

        if self._command_map[key] != urwid.ACTIVATE:
            if key == 'ctrl up':
                if self._selected_index != 0:
                    self._selected_index = self._selected_index - 1

                self.show_choices()
            if key == 'ctrl down':
                if self._selected_index != len(self.choices) - 1:
                    self._selected_index = self._selected_index + 1

                self.show_choices()
            return key

        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        if button != 1 or not urwid.util.is_mouse_press(event):
            return False

        if self._selected_index is None:
            self._selected_index = 0

        self._emit('click')
        return True



if __name__ == '__main__':

    def exit_on_q(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()


    def exit(key):
        raise urwid.ExitMainLoop()


    palette = [
        ('reversed', 'standout', ''),
        ('help', 'white', 'dark green'),

        ('highlight', 'white', 'dark green'),
        ("ilb_highlight_offFocus",    "black",            "dark cyan")
    ]

    view = urwid.Filler(urwid.Pile([
        BoxButton('asdASDASDASDAWDA', on_press=exit),
        BoxButton('asdDQWDQWDQAWD'),
        BoxPicker('Chooseeeeee', choices=[
            '1',
            '2',
            '3',
            '4',
            '5',
        ]),
    ]))

    urwid.MainLoop(view, palette=palette, unhandled_input=exit_on_q).run()
