#!/usr/bin/env python3
"""Prepare an explicitly selected Library partition; never guess a whole disk."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def walk(node):
    yield node
    for child in node.get('children', []):
        yield from walk(child)


def select_partition(disks, device):
    matches = [(disk, node) for disk in disks for node in walk(disk) if node['name'] == device]
    if len(matches) != 1:
        raise ValueError('Choose one existing partition, such as /dev/sdb1.')
    disk, partition = matches[0]
    if disk['type'] != 'disk' or partition['type'] != 'part' or disk.get('ro') or partition.get('ro'):
        raise ValueError('The selected device must be a writable partition on a plain disk.')
    for node in walk(disk):
        for mount in node.get('mountpoints') or []:
            if mount and (mount == '[SWAP]' or mount == '/'
                          or mount.startswith(('/boot', '/usr', '/var', '/etc', '/home'))):
                raise ValueError('Refusing a disk containing system, home, boot or swap filesystems.')
    return disk, partition


def inspect(device):
    disks = json.loads(run('lsblk', '--json', '--bytes', '--paths', '--output',
        'NAME,TYPE,SIZE,RO,MODEL,SERIAL,MAJ:MIN,MOUNTPOINTS,FSTYPE,LABEL,UUID'))['blockdevices']
    disk, part = select_partition(disks, device)
    for node in (disk, part):
        holders = Path('/sys/class/block') / Path(node['name']).name / 'holders'
        if not holders.is_dir() or any(holders.iterdir()):
            raise ValueError('The selected disk/partition is in use by another block device.')
    seq = (Path('/sys/class/block') / Path(disk['name']).name / 'diskseq').read_text().strip()
    return part, (disk['name'], disk['maj:min'], disk['size'], disk.get('serial'), seq,
                  part['name'], part['maj:min'], part['size'], part.get('uuid'))


def confirm_format(device, part, fingerprint):
    print('\n' + '=' * 64, flush=True)
    print('USB DRIVE FORMATTING — ALL FILES ON THE SELECTED PARTITION WILL BE ERASED', flush=True)
    print(f'Device: {device}   Size: {part["size"] / 1024**3:.1f} GiB', flush=True)
    print(f'Filesystem: {part.get("fstype")}   Label: {part.get("label")}', flush=True)
    print('Only this partition will be formatted as exFAT, label Library_USB.', flush=True)
    if not sys.stdin.isatty():
        raise ValueError('Formatting requires the interactive installer terminal; nothing was erased.')
    answer = input(f'Type ERASE {device} to confirm, or press Enter to cancel: ')
    if answer != f'ERASE {device}':
        raise ValueError('Formatting cancelled; nothing was erased.')
    for seconds in range(30, 0, -1):
        print(f'Formatting {device} in {seconds} seconds — Ctrl+C to cancel.', flush=True)
        time.sleep(1)
    current, identity = inspect(device)
    if identity != fingerprint:
        raise ValueError('The selected device changed during confirmation. Nothing was erased.')
    # Reject nested mounts; do not recursively unmount someone else's data.
    for point in current.get('mountpoints') or []:
        if point:
            mounts = json.loads(run('findmnt', '--json', '--submounts', '--mountpoint', point))['filesystems']
            if len(mounts) != 1 or mounts[0].get('children'):
                raise ValueError('Unmount nested filesystems on the selected partition first.')
    for point in current.get('mountpoints') or []:
        if point:
            subprocess.run(['umount', point], check=True)
    current, identity = inspect(device)
    if identity != fingerprint or any(current.get('mountpoints') or []):
        raise ValueError('The selected partition changed or was remounted. Nothing was erased.')
    subprocess.run(['mkfs.exfat', '-n', 'Library_USB', device], check=True)
    subprocess.run(['udevadm', 'settle'], check=True)


def prepare(device, destination, archive, force_format=False):
    device = str(Path(device).resolve(strict=True))
    part, fingerprint = inspect(device)
    # os.path.ismount deliberately returns False for a symlink. Check its
    # target so an existing /Library -> mounted USB layout is preserved.
    destination = Path(destination).resolve()
    if os.path.ismount(destination):
        number = run('findmnt', '--noheadings', '--mountpoint', str(destination), '--output', 'MAJ:MIN')
        if number != part['maj:min']:
            raise ValueError(f'{destination} is mounted from a different device; leaving it alone.')
    elif destination.exists() and any(destination.iterdir()):
        raise ValueError(f'{destination} contains files; refusing to hide them with a mount.')
    formatted = force_format or part.get('label') != 'Library_USB' or part.get('fstype') != 'exfat'
    if formatted:
        if not archive.is_file():
            raise ValueError('The bundled Library_USB.tar is missing; nothing was erased.')
        confirm_format(device, part, fingerprint)
    else:
        print(f'[INFO] {device} is already exFAT Library_USB — keeping all content.', flush=True)
    if os.path.ismount(destination):
        number = run('findmnt', '--noheadings', '--mountpoint', str(destination), '--output', 'MAJ:MIN')
        if number != part['maj:min']:
            raise ValueError(f'{destination} is mounted from a different device; leaving it alone.')
    else:
        if destination.exists() and any(destination.iterdir()):
            raise ValueError(f'{destination} contains files; refusing to hide them with a mount.')
        destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(['mount', device, str(destination.resolve())], check=True)
    if formatted:
        # Only a freshly formatted filesystem receives the bundled seed data.
        subprocess.run(['tar', '-xzf', str(archive), '--no-same-owner', '-C', str(destination)], check=True)
        subprocess.run(['sync'], check=True)
    print(f'[INFO] Library storage ready: {device} at {destination.resolve()}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--mount', type=Path, default=Path('/Library'))
    parser.add_argument('--format', action='store_true')
    parser.add_argument('--archive', type=Path, default=Path(__file__).parent / 'files/Library_USB.tar')
    args = parser.parse_args()
    try:
        prepare(args.device, args.mount, args.archive, args.format)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'USB preparation stopped: {exc}', file=sys.stderr)
        sys.exit(1)
