'''
Created on Nov 15, 2014

@author: cmelton
'''

from optparse import OptionParser
import os, subprocess, time, random

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--C", dest = "command", help = "command to run",
                      metavar = "FILE", type = "string")
    parser.add_option("--F", dest = "filesToCheck", help = "files to check for existence",
                      metavar = "FILE", type = "string", default = "")
    (options, args) = parser.parse_args()
    return options

if __name__ == '__main__':
    options = getOptions()
    command = options.command.split("|")
    outputfiles = [f for f in options.filesToCheck.split("|") if f !=""]
    worked = False
    i = 0
    while not worked:
        i+=1
        print command   
        worked = (subprocess.call(command)==0)
        print worked
        for f in outputfiles:
            if not os.path.exists(f): worked = False
        if i==5: raise Exception
        if not worked: time.sleep(random.randrange(10,100))
        