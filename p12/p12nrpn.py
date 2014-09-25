#!/usr/bin/env python

import os

from collections import namedtuple
from csv import reader as csv_reader


Setting = namedtuple('Setting', ('name', 'number', 'min', 'max'))


def bank_from_csv(filename):
    """Load a bank of NRPN configurations from a CSV file."""
    settings = []
    with open(filename, 'r') as fd:
        reader = csv_reader(fd)
        for row in reader:
            try:
                setting = Setting(
                    name=row[0],
                    number=int(row[1]),
                    min=int(row[2]),
                    max=int(row[3])
                )
                settings.append(setting)
            except Exception:
                print("Could not parse row: %r" % row)
    return settings


def banks_from_dir(dir):
    """Return a dict of banks loaded from CSV files in a directory."""
    banks = {}
    for csv_filename in filter(lambda s: s.endswith('.csv'), os.listdir(dir)):
        bank = csv_filename[:-4]
        banks[bank] = bank_from_csv(os.path.join(dir, csv_filename))
    return banks


def nrpn_command(setting, value, channel=0):
    """Return NRPN messages to set given setting to a value."""
    assert channel < 16
    assert value <= setting.max and value >= setting.min
    n_lsb = setting.number & 0x7F
    n_msb = setting.number >> 7
    v_lsb = value & 0x7F
    v_msb = value >> 7
    status = (0xB << 4) + channel
    # 0x63 = NRPN MSB controller number message
    # 0x62 = NRPN LSB controller number message
    # 0x6 = NRPN MSB data message
    # 0x26 = NRPN LSB data message
    messages = (
        [status, 0x63, n_msb],
        [status, 0x62, n_lsb],
        [status, 0x6, v_msb],
        [status, 0x26, v_lsb]
    )
    return messages


if __name__ == '__main__':
    print(banks_from_dir('lib'))
