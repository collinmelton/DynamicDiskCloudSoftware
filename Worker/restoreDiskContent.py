'''
Created on Sep 14, 2015

@author: cmelton
'''

from optparse import OptionParser
import os
from writeDiskContentFile import getDiskContent

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--P", dest = "pathToDisk", help = "this specifies the path to the disk that should be catologued",
                      metavar = "STRING", type = "string", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/Worker/Test")
    parser.add_option("--F", dest = "diskContentFilename", help = "specifies the name of the file that will contain disk contents",
                      default = "./disk.content")
    (options, args) = parser.parse_args()
    return options

# writes content to a file with each new line separating a filename
def readContentFile(diskContentFilename):
    f = open(diskContentFilename, 'r')
    content = f.read().split("\n")
    f.close()
    return content

def restoreContent(currentContent, previousContent):
    for c in currentContent:
        if c not in previousContent:
            if c[-1]=="/": os.rmdir(c) #will remove an empty directory.
            else: os.remove(c) #will remove a file.
            print "removed", c

if __name__ == '__main__':
    options=getOptions()
    currentContent = getDiskContent(options.pathToDisk)
    if os.path.exists(options.diskContentFilename):
        previousContent = readContentFile(options.diskContentFilename)
        restoreContent(currentContent, previousContent)
    else:
        print "disk content file doesn't exist"