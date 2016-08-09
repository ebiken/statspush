
import os
import sys
import argparse
import logging
import re
import json
import gzip
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

def print_stats(ifstats):
    """test code to print stats selected"""
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

def statspush(dname, fname, pformat="", flag_gzip="False",flag_s3="False"):
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

    # write to stdout if flagged
    if pformat == "cosmetic":
        print_stats(ifstats)
    if pformat == "json":
        print ifstats_json

    # write to gzip file (*.json.gz) or to text file (*.json)
    # (closing file is not required when using "with")
    if flag_gzip:
        filename_gz = dname + "/" + fname + ".gz"
        with gzip.open(filename_gz, 'wb') as f:
            f.write(ifstats_json)
    else:
        filename = dname + "/" + fname
        with open(filename, 'w') as f:
            f.write(ifstats_json)

    # send to aws-s3
    if flag_s3:
        print "debug: send to s3"
        # TODO

### main ###
def main():
    ## parse command line arguments
    parser = argparse.ArgumentParser(
        description="Collect stats and push to file or AWS S3. "
        "File format: stats-YYYYMMDD-hhmmss.json")
    parser.add_argument("--dir", default="/tmp/statspush/",
        help="directory name to store files. default=/tmp/statspush/")
    parser.add_argument("--s3", action="store_true",
        help="upload to AWS S3")
    parser.add_argument("--gzip", action="store_true",
        help="compress using gzip")
    print_options = ["json", "cosmetic"]
    parser.add_argument("-p", "--printstats", choices=print_options,
        help="print stats output to stdout")
    loglevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] 
    parser.add_argument("--loglevel", type=str, choices=loglevels, default="CRITICAL",
        help="configure log level. default=CRITICAL")
    args = parser.parse_args()

    opt_dir     = args.dir
    #opt_dir    = "/home/ebiken/work/statspush/s3/"
    opt_s3      = args.s3
    opt_gzip    = args.gzip
    opt_print   = args.printstats
    set_log_level(args.loglevel)


    ## check if opt_dir exists. create if not.
    d = os.path.dirname(opt_dir)
    if d =='':
        logger.error("S3 directory does not exist; terminating.")
        return
    if not os.path.exists(d):
        os.makedirs(d)

    ## set filename: stats-YYYYMMDD-hhmmss.json
    #filename = "stats-"+time.strftime('%Y%m%d-%H%M%S')+".json" 
    filename = "stats-"+time.strftime('%Y%m%d-%H%M%S')+".json" 

    statspush(opt_dir, filename,
        pformat = opt_print, flag_gzip = opt_gzip, flag_s3 = opt_s3)
    logger.info("pushed %s" % filename)


if __name__ == '__main__':
    main()


