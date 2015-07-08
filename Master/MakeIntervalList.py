'''
Created on Oct 10, 2014

@author: cmelton
'''
from optparse import OptionParser

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--F", dest = "filename", help = "",
                      metavar = "FILE", type = "string", default="test.interval_list")
    parser.add_option("--C", dest = "chroms", help = "",
                      metavar = "STRING", type = "string", default="x y z")
    (options, args) = parser.parse_args()
    return options

if __name__ == '__main__':
    options = getOptions()
    f = open(options.filename, 'w')
    f.write("\n".join(map(lambda x: x.upper(), options.chroms.split(" "))))
    f.close()