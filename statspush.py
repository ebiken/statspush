
import os
import sys
import re
from time import time   # timestamp
#from boto3.s3.connection import S3Connection
#from boto3.s3.key import Key


def interface_stats():
    """Collect insterface stats with timestamp from /proc/net/dev.
    Only works on Linux.
    """
    # set ":" and "space" as key when spliting to stats.
    r = re.compile("[:\s]+")
    ret = {}    # create empty dict used as return value

    f = open("/proc/net/dev", "r")
    timestamp = str(int(time()))
    data = f.read()
    f.close
    
    lines = re.split("[\r\n]+", data)
    # First two lines are headers, so are ignored by lines[2:]:
    for line in lines[2:]:
        line = line.strip()  # remove space on head of line. (ex: lo)
        items = r.split(line)
        # print "debug:", line
        # print "debug: len(items) = ", len(items)
        if len(items) != 17:
            continue
        interface               = items[0]
        rdata = {}
        rdata["timestamp"]      = timestamp
        rdata["rx_bytes"]       = items[1]
        rdata["rx_packets"]     = items[2]
        rdata["rx_errs"]        = items[3]
        rdata["rx_drop"]        = items[4]
        rdata["rx_fifo"]        = items[5]
        rdata["rx_frame"]       = items[6]
        rdata["rx_compressed"]  = items[7]
        rdata["rx_multicast"]   = items[8]
        rdata["tx_bytes"]       = items[9]
        rdata["tx_packets"]     = items[10]
        rdata["tx_errs"]        = items[11]
        rdata["tx_drop"]        = items[12]
        rdata["tx_fifo"]        = items[13]
        rdata["tx_frame"]       = items[14]
        rdata["tx_compressed"]  = items[15]
        rdata["tx_multicast"]   = items[16]
        ret[interface] = rdata

    return ret

def print_stats():
    """test code to print stats"""
    ifstats = interface_stats()
    # print "debug:", ifstats
    for(iface, stats) in ifstats.items():
        print "Interface: %s" % (iface)
        print "  timestamp  = %s" % (stats["timestamp"])
        print "  rx_bytes   = %s" % (stats["rx_bytes"])
        print "  rx_packets = %s" % (stats["rx_packets"])
        print "  tx_bytes   = %s" % (stats["tx_bytes"])
        print "  tx_packets = %s" % (stats["tx_packets"])

def print_stats_all():
    """test code to print stats"""
    ifstats = interface_stats()
    # print "debug:", ifstats
    for(iface, stats) in ifstats.items():
        print "Interface: %s" % (iface)
        for (sname, value) in stats.items():
            print "  %s = %s" % (sname, value)

def statspush():
    """Collect data, format in json, gzip and output

    WRITE DETAILS HERE
    """
    ## debug: print stats
    # print_stats_all()
    # print_stats()
    
    # collect data
    ifstats = interface_stats()
    print ifstats
    # get_data_diff()

    # format data_diff as json format
    #data_json = json (data)
    # gzip
    #data_gzip = gzip (data_json)
    # write to file: host-name/stats-YYYYMMDD-hhmmss.gzip
    # send to aws-s3


### main ###
def main():
    statspush()

if __name__ == '__main__':
    main()
