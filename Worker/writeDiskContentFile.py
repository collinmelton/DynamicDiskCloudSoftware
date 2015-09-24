'''
Created on Sep 14, 2015

@author: cmelton
'''

from optparse import OptionParser
import os

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--P", dest = "pathToDisk", help = "this specifies the path to the disk that should be catologued",
                      metavar = "STRING", type = "string", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/Worker/Test")
    parser.add_option("--F", dest = "diskContentFilename", help = "specifies the name of the file that will contain disk contents",
                      default = "./disk.content")
    (options, args) = parser.parse_args()
    return options

# gets the content of directory and subdirectories and puts in a list
def getDiskContent(path):
    content = set([])
    for root, dirs, files in os.walk(path):
        for name in files: content.add(os.path.join(root, name))
        for dir in dirs: content.add(os.path.join(root, dir)+"/")
#     for c in content: 
#         if c[-1]!="/": 
#             print c
    return content

# writes content to a file with each new line separating a filename
def writeContentToFile(content, diskContentFilename):
    f = open(diskContentFilename, 'w')
    f.write("\n".join(content))
    f.close()

if __name__ == '__main__':
    options=getOptions()
    content = getDiskContent(options.pathToDisk)
    writeContentToFile(content, options.diskContentFilename)