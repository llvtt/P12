import bisect
import cmd
import os
import random
import sys

from functools import wraps

import rtmidi_python

from p12nrpn import (
    banks_from_dir,
    nrpn_command,
    Setting,
    ALLOWED_NAME_CHARACTERS
)


MIDI = rtmidi_python.MidiOut()
CHANNEL = 0


def ignore_value_error(f):
    @wraps(f)
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
        here = os.path.dirname(os.path.abspath(__file__))
        self.banks = banks_from_dir(os.path.join(here, os.pardir, 'lib'))
        self.settings = [s for bank in self.banks for s in self.banks[bank]]
        nprn_number_of = lambda x: x.number
        self.settings.sort(key=nprn_number_of)
        self.settings_keys = map(nprn_number_of, self.settings)

    def _show_setting(self, setting):
        print('%d. %s' % (setting[1], setting[0]))

    def _layer_1_from_layer_0(self, setting):
        # TODO: this is kind of hacky.
        setting = Setting(setting.name, setting.number + 512,
                          setting.min, setting.max)
        return setting

    def __output_value(self, setting, value):
        messages = nrpn_command(setting, value)
        for message in messages:
            MIDI.send_message(message)

    def _output_value(self, setting, value, layer=0):
        if layer != 'both':
            # Skip "split point" and "a/b mode" settings.
            if setting.number in (287, 288):
                return False
        if layer == 0 or layer == 'both':
            self.__output_value(setting, value)
        if layer == 1 or layer == 'both':
            self.__output_value(self._layer_1_from_layer_0(setting), value)
        return True

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
        global CHANNEL
        if not command:
            print(CHANNEL)
        else:
            CHANNEL = int(command)
            print(CHANNEL)

    def do_name(self, command):
        """Name the current patch.

        USAGE: name <layer0 name> [layer1 name]
        """
        names = command.strip().split()
        if not names or len(names) > 2:
            print("name <layer0 name> [layer1 name]")
            return

        name_nrpn_start = 480
        for i in range(len(names)):
            name = names[i]
            # Names must be 20 or fewer characters.
            if len(name) > 20:
                print("Names must be 20 characters or fewer, but "
                      "%s is %d characters." % (name, len(name)))
                return
            # Validate name characters.
            for letter in name:
                if ord(letter) not in ALLOWED_NAME_CHARACTERS:
                    print("Character %s is not allowed in layer names."
                          % letter)
            for index, letter in enumerate(name):
                # TODO: move this to lib?
                name_setting = Setting('layer name',
                                       name_nrpn_start + index + (512 * i),
                                       ord('A'), ord('z'))
                value = ord(letter)
                self._output_value(name_setting, value)

    @ignore_value_error
    def do_out(self, command):
        """Output a specified, or random, value to a setting.

        USAGE: out <nprn number|bank|all> [value = random] [layer = 0[|1|both]]
        """
        args = command.split()
        if not len(args) > 0:
            print('out <nprn number|bank|all> [value = random] '
                  '[layer = 0[|1|both]]')
        else:
            nrpn = args[0]
            layer = 0
            if nrpn != 'all' and nrpn not in self.banks:
                nrpn = int(nrpn)
            use_random = True
            if len(args) >= 2 and args[1] != 'random':
                value = int(args[1])
                use_random = False
            elif len(args) == 3:
                layer = args[2]
            if nrpn == 'all':
                for setting in self.settings:
                    if use_random:
                        value = random.randint(setting.min, setting.max)
                    self._output_value(setting, value, layer=layer)
            elif nrpn in self.banks:
                bank_settings = self.banks[nrpn]
                for setting in bank_settings:
                    if use_random:
                        value = random.randint(setting.min, setting.max)
                    self._output_value(setting, value, layer=layer)
            else:
                setting = self._setting(nrpn)
                if use_random:
                    value = random.randint(setting.min, setting.max)
                self._output_value(setting, value, layer=layer)

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
