
import os
import sys
import argparse
import logging
import re
import json
import gzip
import time # timestamp, time
import boto3
import botocore
import urllib2

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

def get_iflist():
    """Wrapper to get list of network interfaces on Linux"""
    return os.listdir("/sys/class/net/")

def interface_stats_zebra():
    """Collect insterface stats from zebra REST interface.
    Add timestamp and interface name to the return data.
    Only works while openconfigd and zebra/ribd are running.
    """
    ret = {}    # create empty dict used as return value
    timestamp = int(time.time())

    iflist = get_iflist()
    for ifname in iflist:
        # GET data from zebra/ribd REST interface
        data = json.load(urllib2.urlopen("http://localhost:3000/interfaces/interfaces-state/%s/statistics" % ifname))
        data["timestamp"] = timestamp
        ret[ifname] = data

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

### DEFINITION OF FLAGS
FLAGS_S3    = "s3" 
FLAGS_GZIP  = "gzip"
FLAGS_ZEBRA = "zebra"

def statspush(dname, fname, flags, s3bucket="statspush", pformat=""):
    """Collect data, format in json, gzip and output

    dname: directory name to store file.
    fname: name of the file to write stats to.
    pformat: format when printing to stdout.
        json: json format
    flags:
        FLAGS_S3: push file to AWS S3
        FLAGS_GZIP: compress file using gzip
    """
    ## check if dname exists and write accessible. create if it didn't exist.
    check_create_dir(dname)
    
    # collect data
    # TODO: add delta stats
    if FLAGS_ZEBRA in flags:
        ifstats = interface_stats_zebra()
    else:
        ifstats = interface_stats()
    
    # serialize in json
    ifstats_json = json.dumps(ifstats)
    fname = fname + ".json"
    logger.debug("fname in json = %s" % fname)

    # write to stdout if flagged
    if pformat == "json":
        print ifstats_json

    # write to gzip file (*.json.gz) or to text file (*.json)
    # (closing file is not required when using "with")
    if FLAGS_GZIP in flags:
        fname = fname + ".gz"
        filename = dname + "/" + fname
        with gzip.open(filename, 'wb') as f:
            f.write(ifstats_json)
    else:
        filename = dname + "/" + fname
        with open(filename, 'w') as f:
            f.write(ifstats_json)
    logger.debug("Written stats to filename: %s" % filename)

    # push file to AWS S3
    if FLAGS_S3 in flags:
        s3 = boto3.client('s3')
        s3.upload_file(filename, s3bucket, fname)
        logger.debug("Pushed file to AWS S3.")

def check_create_dir(opt_dir):
    if os.path.isdir(opt_dir):
        if os.access(opt_dir, os.W_OK):
            logger.debug("Directory exists and write accessible: %s" % opt_dir)
        else:
            logger.critical("Did not have write access: %s" % opt_dir)
            exit()
    else:
        # return if opt_dir was file.
        if os.path.isfile(opt_dir):
            logger.critical("Not directory but file: %s" % opt_dir)
            exit()
        # create if opt_dir doesn't exist.
        try:
            os.makedirs(opt_dir)
        except OSError:
            logger.critical("Could not create directory: %s" % opt_dir)
            raise

### main ###
def main():
    ## parse command line arguments
    parser = argparse.ArgumentParser(
        description="Collect stats and push to file or AWS S3. "
        "File format: stats-YYYYMMDD-hhmmss.json")
    # values
    parser.add_argument("-d", "--dir", default="/tmp/statspush/",
        help="directory name to store files. default=/tmp/statspush/")
    parser.add_argument("--s3bucket", default="statspush",
        help="AWS S3 bucket name to store files. default=statspush")
    print_options = ["json"]
    parser.add_argument("-p", "--printstats", choices=print_options,
        help="print stats output to stdout")
    loglevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] 
    parser.add_argument("--loglevel", type=str, choices=loglevels, default="CRITICAL",
        help="configure log level. default=CRITICAL")
    # flags
    parser.add_argument("--s3", action="store_true",
        help="upload to AWS S3")
    parser.add_argument("--gzip", action="store_true",
        help="compress using gzip")
    parser.add_argument("--zebra", action="store_true",
        help="get data from zebra REST interface")

    args = parser.parse_args()
    set_log_level(args.loglevel)    # log level must be set first.
    # values
    opt_dir     = os.path.abspath(args.dir)
    logger.debug("os.path.abspath(args.dir): %s" % opt_dir)
    opt_s3bucket = args.s3bucket
    opt_print   = args.printstats
    # flags
    flags = []
    if args.s3:
        flags.append(FLAGS_S3)
    if args.gzip:
        flags.append(FLAGS_GZIP)
    if args.zebra:
        flags.append(FLAGS_ZEBRA)
    logger.debug("flags = %s" % flags)

    ## set filename: stats-YYYYMMDD-hhmmss.json
    filename = "stats-"+time.strftime('%Y%m%d-%H%M%S')

    statspush(opt_dir, filename, flags, opt_s3bucket, pformat = opt_print)
    logger.info("pushed %s" % filename)


if __name__ == '__main__':
    main()

