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
            urwid.Button(device.path, on_press=self.replaceDevice, user_data=device.path) for device in self.currentDevices()
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


if __name__ == '__main__':

    def exit_on_q(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()


    palette = [
        ('reversed', 'standout', ''),
        ('help', 'white', 'dark green', 'underline')
    ]

    view = PartitionTable()

    urwid.MainLoop(view, palette=palette, unhandled_input=exit_on_q).run()

    print(view.processResult())
