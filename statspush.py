
import os
import sys
import re
import json
import gzip
import logging
import time # timestamp, time
#from boto3.s3.connection import S3Connection
#from boto3.s3.key import Key


### define logger here so it can be accessed from any place in this module.
## Logger should be replaced to use config file (logging.config) as described below.
## * https://docs.python.org/2.7/howto/logging.html
## * https://docs.python.org/2.7/library/logging.config.html#logging-config-api
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.CRITICAL)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def set_log_level(level):
    logger.debug("entered set_log_level")

    loglevel = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in loglevel:
        return
    # ch = logging.StreamHandler()
    # TODO: add code to select Handler.
    logger.debug("setting log level")
    if level == "DEBUG":
        ch.setLevel(logging.DEBUG)
    elif level == "INFO":
        ch.setLevel(logging.INFO)
    elif level == "WARNING":
        ch.setLevel(logging.WARNING)
    elif level == "ERROR":
        ch.setLevel(logging.ERROR)
    elif level == "CRITICAL":
        ch.setLevel(logging.CRITICAL)

    # ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

def interface_stats():
    """Collect insterface stats with timestamp from /proc/net/dev.
    Only works on Linux.
    """
    # set ":" and "space" as key when spliting to stats.
    r = re.compile("[:\s]+")
    ret = {}    # create empty dict used as return value

    f = open("/proc/net/dev", "r")
    timestamp = int(time.time())
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
        rdata["rx_bytes"]       = int(items[1])
        rdata["rx_packets"]     = int(items[2])
        rdata["rx_errs"]        = int(items[3])
        rdata["rx_drop"]        = int(items[4])
        rdata["rx_fifo"]        = int(items[5])
        rdata["rx_frame"]       = int(items[6])
        rdata["rx_compressed"]  = int(items[7])
        rdata["rx_multicast"]   = int(items[8])
        rdata["tx_bytes"]       = int(items[9])
        rdata["tx_packets"]     = int(items[10])
        rdata["tx_errs"]        = int(items[11])
        rdata["tx_drop"]        = int(items[12])
        rdata["tx_fifo"]        = int(items[13])
        rdata["tx_frame"]       = int(items[14])
        rdata["tx_compressed"]  = int(items[15])
        rdata["tx_multicast"]   = int(items[16])
        ret[interface] = rdata

    return ret

def print_stats():
    """test code to print stats selected"""
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

def statspush(dname, fname):
    """Collect data, format in json, gzip and output

    WRITE DETAILS HERE
    """
    ## debug: print stats
    # print_stats_all()
    # print_stats()
    
    # collect data
    ifstats = interface_stats()

    # serialize in json
    ifstats_json = json.dumps(ifstats)

    ## (closing file is not required when using "with")
    ## write to text file (*.json)
    filename = dname + "/" + fname
    with open(filename, 'w') as f:
        f.write(ifstats_json)
    # write to gzip file (*.json.gz)
    filename_gz = dname + "/" + fname + ".gz"
    with gzip.open(filename_gz, 'wb') as f:
        f.write(ifstats_json)

    # send to aws-s3


### main ###
def main():
    ## s3dir = argv[1]
    s3dir = "/home/ebiken/work/statspush/s3/"
#    s3dir = "aaa.txt"

    ## set log level from argv
    # TODO: set log level from argv
    loglevel = "ERROR"
    loglevel = "INFO"
    set_log_level(loglevel)

    ## check if s3dir exists. create if not.
    d = os.path.dirname(s3dir)
    if d =='':
        logger.error("S3 directory does not exist; terminating.")
        return
    if not os.path.exists(d):
        os.makedirs(d)

    ## set filename: stats-YYYYMMDD-HHMMSS.json
    #filename = "stats-"+time.strftime('%Y%m%d-%H%M%S')+".json" 
    filename = "stats-"+time.strftime('%Y%m%d-%H%M%S')+".json" 
    statspush(s3dir, filename)
    logger.info("pushed %s" % filename)

    ## s3label? = argv[2]
    ##  -> make these as options ex: "-s3 <s3dir> -s3label <s3label>"

if __name__ == '__main__':
    main()


