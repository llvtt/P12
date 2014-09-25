import bisect
import cmd
import os
import random
import sys

import rtmidi_python

from p12nrpn import (
    banks_from_dir,
    nrpn_command
)


MIDI = rtmidi_python.MidiOut()
CHANNEL = 0


def ignore_value_error(f):
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            print(str(e))
    return wrap


class P12CLI(cmd.Cmd):
    """Command-line interface to the Prophet 12."""

    def __init__(self, *args, **kwargs):
        cmd.Cmd.__init__(self, *args, **kwargs)
        self.banks = banks_from_dir(os.path.join(os.pardir, 'lib'))
        self.settings = [s for bank in self.banks for s in self.banks[bank]]
        nprn_number_of = lambda x: x.number
        self.settings.sort(key=nprn_number_of)
        self.settings_keys = map(nprn_number_of, self.settings)

    def _show_setting(self, setting):
        print('%d. %s' % (setting[1], setting[0]))

    def _output_value(self, setting, value):
        messages = nrpn_command(setting, value)
        for message in messages:
            MIDI.send_message(message)

    def _setting(self, nprn):
        # Binary search.
        setting_number = bisect.bisect_left(self.settings_keys, nprn)
        if setting_number < len(self.settings) and setting_number > 0:
            setting = self.settings[setting_number]
            if setting.number == nprn:
                return self.settings[setting_number]

    @ignore_value_error
    def do_channel(self, command):
        """Change or print the current MIDI channel."""
        command = command.strip()
        if not command:
            print(CHANNEL)
        else:
            global CHANNEL
            CHANNEL = int(command)
            print(CHANNEL)

    @ignore_value_error
    def do_out(self, command):
        """Output a specified, or random, value to a setting."""
        args = command.split()
        if not len(args) > 0:
            print('out <nprn number|bank|all> [value = random]')
        else:
            nrpn = args[0]
            if nrpn != 'all':
                nrpn = int(nrpn)
            value = 'random'
            if len(args) == 2 and args[1] != 'random':
                value = int(args[1])
            if nrpn == 'all':
                for setting in self.settings:
                    if value == 'random':
                        value = random.randint(setting.min, setting.max)
                    self._output_value(setting, value)
            else:
                setting = self._setting(nrpn)
                if value == 'random':
                    value = random.randint(setting.min, setting.max)
                self._output_value(setting, value)

    @ignore_value_error
    def do_show(self, command):
        nprn = int(command.strip())
        setting = self._setting(nprn)
        if setting:
            print("====== %s ======" % setting.name)
            print("NPRN:                %d" % setting.number)
            print("Minimum value:       %d" % setting.min)
            print("Maximum value:       %d" % setting.max)
        else:
            print("No setting with NPRN number %d." % nprn)

    @ignore_value_error
    def do_midi(self, command):
        """With no argument, list available MIDI output ports.
        With a port number, connect to that MIDI port.

        """
        command = command.strip()
        if not command:
            if not MIDI.ports:
                print("No available MIDI ports. "
                      "Connect a MIDI device and restart.")
            else:
                print('\n'.join(MIDI.ports))
        else:
            MIDI.open_port(int(command))

    @ignore_value_error
    def do_ls(self, command):
        """With no argument, print available banks.
        With a bank name, print settings within that bank.

        """
        command = command.strip()
        if not command:
            print("Available banks for the Prophet 12:")
            print('\n'.join(self.banks))
        args = command.split()
        if len(args) > 0 and args[0] in self.banks:
            bank = self.banks[args[0]]
            end = int(args[1]) if len(args) > 1 else len(bank)
            for i in range(end):
                self._show_setting(bank[i])
        elif len(args) > 0:
            for setting in self.settings:
                self._show_setting(setting)

    def do_quit(self, command):
        """Leave the Prophet 12 command-line interface."""
        sys.exit(0)

    do_EOF = do_quit


if __name__ == '__main__':
    P12CLI().cmdloop()
