'''
Created on Mar 25, 2016

@author: cmelton
'''

import pickle
import sys

from optparse import OptionParser
import InstanceData

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--H", dest = "historyFile", help = "this should be a history pickle file with info about the job",
                      metavar = "FILE", type = "string", default="/home/cmelton/DynamicDiskCloudSoftware/Master/TestData/test1-node-1-stepa.history.pickle")
    (options, args) = parser.parse_args()
    return options

if __name__ == '__main__':
    options = getOptions()
    f=open(options.historyFile)
    data = pickle.load(f)
    f.close()
    print data["CommandData"].commands