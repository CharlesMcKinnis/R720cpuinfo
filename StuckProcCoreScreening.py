#!/usr/bin/env python2
"""
This script identifies the max speed of CPUs based on the model name, then monitors the cores for speed stepping.
The goal is to retain the highest speed and identify cores that are not scaling properly.
monitor /proc/cpuinfo and track for changes
"""

import re
from time import sleep
import sys
try:
    import argparse
    ARGPARSE = True
except:
    ARGPARSE = False

class argsAlt(object):
    pass

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value

class ansi:

    """
    This class is to display different color fonts
    example:
    print "Testing a color    [ %sOK%s ]" % (
        ansi.CYAN,
        ansi.ENDC
                    )
    or to avoid a new line
    import sys
    sys.stdout.write("%s%s" % (ansi.CLR,ansi.HOME))
    """
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CLR = '\033[2J'
    HOME = '\033[H'
    def clear(self):
        sys.stdout.write("%s%s" % (ansi.CLR,ansi.HOME))
    def home(self):
        sys.stdout.write("%s" % ansi.HOME)

def all_clear(cpuspeed):
    allclear = 1
    for key in cpuspeed:
        if cpuspeed[key]["mhz"]==1200:
            allclear=0
        elif not cpuspeed[key]["mhz"] >= cpuspeed[key]["maxmhz"]:
            allclear=0
    return(allclear)

def screen_print(cpuspeed, cycle_counter, **kwargs):
    """
    kwargs:
    clear_screen = True
    Clear the screen instead of just going to home
    
    no_ansi = True
    Omit ansi characters for home, clear screen and colors
    
    no_runtime = True
    Do not print "ctrl+c" and seconds runtime
    
    """
    if "clear_screen" in kwargs:
        sys.stdout.write("%s%s" % (ansi.CLR,ansi.HOME))
    elif not "no_ansi" in kwargs:
        sys.stdout.write("%s" % (ansi.HOME,))
    print "A healthy and busy system should show MHz in increments of 100 (or XX01 at full speed) and hit full speed on all CPUs in 30-60 seconds.\n"
    for key, value in sorted(cpuspeed.items()):
        # "stuck" CPUs tend to stay at 1200MHz, so flag those as red
        # If the CPU hit the model's max, or 1 over max if it is static, flag it green
        # If the CPU is in between, mark it yellow
        print "CPU : %s, Model: %s, Max: %s" % (key,cpuspeed[key]["model"],cpuspeed[key]["maxmhz"])
        if not "no_ansi" in kwargs:
            if cpuspeed[key]["mhz"]==1200:
                status_color=ansi.RED
            elif not cpuspeed[key]["mhz"] >= cpuspeed[key]["maxmhz"]:
                status_color=ansi.YELLOW
            else:
                status_color=ansi.GREEN
        else:
            status_color=""
        print "Max observed speed: %s%s%s" % (status_color,cpuspeed[key]["mhz"],ansi.ENDC)
    if not "no_runtime" in kwargs:
        print "\nCtrl+C to exit, Runtime: %5.1f seconds" % (float(cycle_counter)/10,)
    return(allclear)

if ARGPARSE:
    parser = argparse.ArgumentParser()
    parser.add_argument("-r","--runtime", help="Maximum number of seconds to watch the CPUs before ending",
                        type=int)
    parser.add_argument("-s","--silent",
                        help="No output, return code of 0 if CPUs are clear, and non-zero if the CPUs do not hit max within the runtime specified. Default 30 seconds, use --runtime to specify the duration.",
                        action="store_true")
    parser.add_argument("-b","--batch", help="Run for a time, then output results. Default 30 seconds, use --runtime to specify the duration.",
                        action="store_true")
    parser.add_argument("--plaintext", help="ANSI control characters are omitted for colors and screen clear/home.",
                        action="store_true")
    args = parser.parse_args()
else:
    args = argsAlt()
    # dummy class in the event argparse is not available on the system

if not sys.stdout.isatty():
    # not interactively
    print "batch mode"
    args.batch = True

if (args.silent or args.batch) and not args.runtime:
    args.runtime = 30
    pass
if args.batch:
    args.plaintext = True
if args.batch:
    pass

cpuspeed = AutoVivification()
cycle_counter = 0
allclear = 0

if not (args.silent or args.plaintext):
    sys.stdout.write("%s%s" % (ansi.CLR,ansi.HOME))

try:
    while allclear == 0:
        infile = open('/proc/cpuinfo', 'r')
        cpuinfo = infile.readlines()
        cpu=""
        for line in cpuinfo:
            # cpu
            # model
            # mhz
            result = re.match('(processor|model name|cpu MHz)[\s:]+(\d*)(.*)', line.strip())
            # group 1 is category
            # group 2 is numbers (speed or processor number)
            # group 3 is anything following numbers (model name)
    
            if not result:
                continue
            if result.group(1)=="processor":
                # which CPU core are we talking about?
                cpu = int(result.group(2))
            elif result.group(1)=="model name" and not "model" in cpuspeed[cpu]:
                # we only set the model if it isn't already set, and we get the max speed at the same time too
                cpuspeed[cpu]["model"]=result.group(3)
                result = re.search('([\d\.]+)GHz', line.strip())
                cpuspeed[cpu]["maxmhz"]=int(float(re.search('([\d\.]+)GHz', line.strip()).group(1))*1000)
            elif result.group(1)=="cpu MHz":
                # you can't reference the variable that isn't set, so max alone doesn't work
                if not "mhz" in cpuspeed[cpu]:
                    cpuspeed[cpu]["mhz"]=int(result.group(2))
                else:
                    cpuspeed[cpu]["mhz"]=max(cpuspeed[cpu]["mhz"],int(result.group(2)))
        # assume all the CPUs are good (allclear), then test for lower states. Exit if they are all clear.
        allclear = all_clear(cpuspeed)
        if not (args.silent or args.batch):
            if args.plaintext:
                screen_print(cpuspeed, cycle_counter, no_ansi = True)
            else:
                screen_print(cpuspeed, cycle_counter)
        if args.runtime and (cycle_counter/10 >= args.runtime):
            allclear = 2
        infile.close()
        cycle_counter+=1
        sleep(.1)
except KeyboardInterrupt:
    #allclear = all_clear(cpuspeed)
    screen_print(cpuspeed, cycle_counter)
    sys.exit(128)

if args.plaintext:
    screen_print(cpuspeed, cycle_counter, no_ansi = True, no_runtime = True)
    pass

if allclear==1:
    if not args.silent:
        print "All CPUs cleared in %d seconds" % (cycle_counter/10)
    else:
        sys.exit(0)
elif allclear==2:
    plural=""
    if cycle_counter/10 > 1:
        plural="s"
    if not args.silent:
        print "CPUs did not clear during the test run, stopped after %d second%s" % ((cycle_counter/10), plural)
    sys.exit(1)