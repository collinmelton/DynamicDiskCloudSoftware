'''
Created on Sep 14, 2015

@author: cmelton
'''

from optparse import OptionParser
import os
from writeDiskContentFile import getDiskContent, writeContentToFile, getDiskContent

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--P", dest = "pathToDisk", help = "this specifies the path to the disk that should be catologued",
                      metavar = "STRING", type = "string", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/Worker/Test")
    parser.add_option("--F", dest = "diskContentFilename", help = "specifies the name of the file that will contain disk contents",
                      default = "./disk.content")
    parser.add_option("--V", dest = "verbose", help = "verbose, T or F",
                      default = "T")
    (options, args) = parser.parse_args()
    return options

# writes content to a file with each new line separating a filename
def readContentFile(diskContentFilename, verbose):
    f = open(diskContentFilename, 'r')
    content = f.read().split("\n")+[diskContentFilename]
    f.close()
    if verbose: print content
    return content

def restoreContent(currentContent, previousContent, verbose):
    for c in currentContent:
        if c not in previousContent:
            if c[-1]=="/": os.rmdir(c) #will remove an empty directory.
            else: os.remove(c) #will remove a file.
            if verbose: print "removed", c
        else:
            if verbose: print "kept", c

if __name__ == '__main__':
    options=getOptions()
    currentContent = getDiskContent(options.pathToDisk)
    verbose = (options.verbose=="T")
    if os.path.exists(options.diskContentFilename):
        previousContent = readContentFile(options.diskContentFilename, verbose)
        restoreContent(currentContent, previousContent, verbose)
    else:
        if verbose:
            print "disk content file doesn't exist"
        # write content file if none exists
        writeContentToFile(getDiskContent(options.pathToDisk), options.diskContentFilename)
    