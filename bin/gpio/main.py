#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import argparse
import glob
import os
import sys
import grp

defaults = {
    'config': 'gpio.conf'
}


def get_gpio_name(gpio_path, pin):
    name = glob.glob("{}/gpio{}_*".format(gpio_path, pin))
    if name:
        return name[0].split('/')[-1]
    else:
        return False



def main(args):

    if args.config:
        config_file = args.config
    else:
        config_file = defaults['config']

    if args.verbose:
        print(" | config_file = {}".format(config_file))

    config = configparser.ConfigParser()
    # Try to read config file.
    if not config.read(config_file):
        print("E: Can't read config file: {}".format(config_file), file=sys.stderr)
        exit()

    # Check existence of required sections in config file
    err = False
    sections = ('Paths', 'Permissions', 'GPIO')
    for section in sections:
        if not err and not section in config:
            print("E: Could not find section '{}' in config file".format(section))
            err = True

    paths = config['Paths']
    permissions = config['Permissions']
    gpio = config['GPIO']

    if args.verbose:
        print(" | checking config")

    # Check file paths from config file
    err = False
    if not err and not os.path.exists(paths['GPIO_Path']):
        print("E: '{}' is not valid GPIO_Path".format(paths['GPIO_Path']), file=sys.stderr)
        err = True
    if not err and not os.path.exists(paths['GPIO_Export']):
        print("E: '{}' is not valid GPIO_Export".format(paths['GPIO_Export']), file=sys.stderr)
        err = True
    if not err and not os.path.exists(paths['GPIO_Unexport']):
        print("E: '{}' is not valid GPIO_Unexport".format(paths['GPIO_Unexport']), file=sys.stderr)
        err = True

    # Check existence of group from config file
    with open('/etc/group', 'r') as group_file:
        groups = group_file.read()
        if not err and not permissions['GPIO_Group'] in groups:
            print("E: Could not find '{}' group in '/etc/group' file".format(permissions['GPIO_Group']), file=sys.stderr)
            err = True
        if not err and args.verbose:
            print(" + group '{}' found".format(permissions['GPIO_Group']))

    if err:
        print(" Errors occured. Check your config file.")
        exit()

    if args.verbose:
        print(" + config clean, checking GPIO")

    for pin in gpio:
        (gpio_dir, gpio_val) = gpio[pin].split(',')
        if args.verbose:
            print()
            print(" ++ pin: {}".format(pin))
            print(" +  dir: {}".format(gpio_dir))
            print(" +  val: {}".format(gpio_val))
            print(" + trying to find pin dir")
        gpio_name = get_gpio_name(paths['GPIO_Path'], pin)
        dir_set = False
        val_set = False
        grp_set = False
        if gpio_name:
            if args.verbose:
                print(" +  found dir: '{}'".format(gpio_name))
                print(" + checking permissions")
            if grp.getgrnam(permissions['GPIO_Group']) ==\
                grp.getgrgid(os.stat(paths['GPIO_Directory'].format(gpio_name)).st_gid):
                if args.verbose:
                    print(" +  '{}' group is set to '{}'".format(gpio_name, permissions['GPIO_Group']))
            else:
                grp_set = True


            if args.verbose:
                print(" + checking direction and value")
            with open(paths['GPIO_Direction'].format(gpio_name), 'r') as d:
                if  d.read().strip() == gpio_dir:
                    if args.verbose:
                        print(" +  '{}' direction OK ({})".format(gpio_name, gpio_dir))
                else:
                    dir_set = True
            if gpio_dir == 'out':
                with open(paths['GPIO_Value'].format(gpio_name), 'r') as v:
                    if v.read().strip() == gpio_val:
                        if args.verbose:
                            print(" +  '{}' value OK ({})".format(gpio_name, gpio_val))
                    else:
                        val_set = True
        else:
            if args.verbose:
                print("  -  not found - exporting")
            with open(paths['GPIO_Export'], 'w') as e:
                e.write(pin)
            gpio_name = get_gpio_name(paths['GPIO_Path'], pin)
            if args.verbose:
                print(" +  gpio_name: {}".format(gpio_name))
            dir_set = True
            val_set = True
            grp_set = True

        if gpio_dir == 'in':
            val_set = False

        if dir_set:
            with open(paths['GPIO_Direction'].format(gpio_name), 'w') as d:
                if args.verbose:
                    print(" | setting '{}' direction to '{}'".format(gpio_name, gpio_dir))
                d.write(gpio_dir)
        if val_set:
            with open(paths['GPIO_Value'].format(gpio_name), 'w') as v:
                if args.verbose:
                    print(" | setting '{}' value to '{}'".format(gpio_name, gpio_val))
                v.write(gpio_val)

        if grp_set:
            if args.verbose:
                print(" | changing '{}' group to '{}".format(gpio_name, permissions['GPIO_Group']))
            os.chown(paths['GPIO_Directory'].format(gpio_name), -1,
                grp.getgrnam(permissions['GPIO_Group']).gr_gid)
            os.chown(paths['GPIO_Direction'].format(gpio_name), -1,
                grp.getgrnam(permissions['GPIO_Group']).gr_gid)
            os.chown(paths['GPIO_Value'].format(gpio_name), -1,
                grp.getgrnam(permissions['GPIO_Group']).gr_gid)

    if args.verbose:
        print("Done")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GPIO setup script',
                                     epilog='Must be run as root')
    parser.add_argument('-c', '--config', help='path to config file',
                        metavar='config')
    parser.add_argument('-v', '--verbose', help='turn on verbosity',
                        action='store_true')
    args = parser.parse_args()

    # Check if current user is root
    if os.getuid():
        # If not - display help message and exit
        parser.parse_args(['-h',])

    main(args)
