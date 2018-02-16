#!/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import re
from subprocess import CalledProcessError, check_output
import configargparse
import os
import shutil
import datetime
from xml.dom import minidom
import logging

logging.basicConfig(level=logging.DEBUG, filename='/var/log/ovirt-vm-backup/restore.log',
                    format='%(asctime)s %(levelname)s %(message)s', datefmt='%F %T')
fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%F %T')
stderrLogger = logging.StreamHandler()
stderrLogger.setFormatter(fmt)
logging.getLogger().addHandler(stderrLogger)
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")


def args():
    p = configargparse.ArgParser(
        default_config_files=['/etc/restore.cfg'],
        version='0.2'
    )
    p.add_argument('-c', '--config', is_config_file=True, help='config file path')
    p.add_argument('-P', '--path', help='path of export domain')
    p.add_argument('dir', help='name of directory in TSM')

    options = p.parse_args()
    directory = options.dir
    export_path = options.path
    return export_path, directory


def get_tsm(path, directory):
    """
    Execute dsmc command for Retrieve backup from TSM IBM
    @param path: url where store restore files
    @param directory: name of store backup
    @return: 1 if OK
    """
    global timestamp
    try:
        check_output(["sudo", "dsmc", "retrieve", os.path.join(path, directory) + "/", "-subdir=yes"])
        return 1
    except CalledProcessError as error:
        logging.error('%s dsmc exit with error %s', timestamp, error.returncode)
        return error.returncode


def ovf_get(vm_path):
    for root, dirs, files in os.walk(vm_path):
        for file in files:
            if file.endswith(".ovf"):
                return os.path.join(root, file), root


def parse_xml(xml_path):
    xml_ovf = minidom.parse(xml_path)
    disks = xml_ovf.getElementsByTagName('Disk')
    dgroups = list()
    for disk in range(len(disks)):
        disk_split = disks[disk].attributes["ovf:fileRef"].value
        dgroups.append(disk_split.split("/")[0])
    return dgroups


def restore_imgs(disksg, imgs, export_imgs):
    global timestamp
    try:
        for disk in disksg:
            disk_src = os.path.join(imgs, disk)
            logging.info('%s moving %s to %s', timestamp, disk_src, export_imgs)
            shutil.move(disk_src, export_imgs)
    except Exception as e:
        return e
        # logging.error('%s an error encountered when moving images: %s', timestamp, e)


def export_path_id(path):
    pattern = '[\w]{8}(-[\w]{4}){3}-[\w]{12}$'
    for f in os.listdir(path):
        if re.search(pattern, f):
            folder = os.path.join(path, f)
            if os.path.isdir(folder):
                return folder


def restore(path, directory):
    global timestamp
    try:
        path_export = export_path_id(path=path)
        imgs = os.path.join(path, directory, "images")
        vms = os.path.join(path, directory, "master", "vms")
        export_imgs = os.path.join(path_export, "images")
        ovf, dir_vm = ovf_get(vms)
        disksg = parse_xml(ovf)
        restore_imgs(disksg=disksg, imgs=imgs, export_imgs=export_imgs)
        export_vms = os.path.join(path_export, "master", "vms")
        shutil.move(dir_vm, export_vms)
    except OSError as e:
        logging.error('%s restore process failed error: %s', timestamp, e)
        exit(2)


def main():
    global timestamp
    path, directory = args()
    if not os.path.exists(path):
        logging.info('%s path not found', timestamp, path)
    else:
        logging.info('%s Init restore for %s', timestamp, directory)
        logging.info('%s Get %s from TSM', timestamp, directory)
        if get_tsm(path=path, directory=directory):
            restore(path=path, directory=directory)
            shutil.rmtree(os.path.join(path, directory))
            logging.info('%s Restore of %s successfully completed', timestamp, directory)
            exit(0)
        else:
            logging.info('%s TSM not find %s backup', timestamp, directory)
            exit(1)


if __name__ == '__main__':
    main()
