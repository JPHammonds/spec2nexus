#!/usr/bin/env python

#-----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2014-2019, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
read a list of SPEC data files (or directories) and plot images of all scans

.. autosummary::

    ~DirectoryNotFoundError
    ~PlotSpecFileScans
    ~Cache_File_Mtime
    ~datePath
    ~getSpecFileDate
    ~needToMakePlot
    ~timestamp
    ~buildIndexHtml
    ~logger

.. rubric:: RESULT

The images are stored in files within a directory structure
that is organized chronologically,
such as: ``yyyy/mm/spec_file/s1.svg``.
The root of the directory is either specified by the 
command line ``-d`` option or  defaults to the current 
working directory.  The ``yyyy/mm`` (year and month) are 
taken from the ``#D`` line of the SPEC data file.
The ``spec_file`` is the file name with file extension 
and directory name removed.  The image file names are
derived from the scan numbers.

.. rubric:: Linux CRON task

This script could be called from a *cron* entry, such as::

    # every five minutes (generates no output from outer script)
    0-59/5 * * * *  /some/directory/specplot_gallery.py -d /web/page/dir /spec/data/file/dir

If this script is called too frequently and the list of plots to be generated
is large enough, it is possible for more than one process to be running.
In one extreme case, many processes were found running due to problems with the data files.
To identify and stop all processes of this program::

    kill -9 `ps -ef | grep python | awk '/specplot_gallery.py/ {print $2}' -`

"""


import datetime
import json
import logging
import os
import shutil
import sys

from . import spec
from . import specplot

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError     # py27 compatibility


MTIME_CACHE_FILE = 'mtime_cache.json'
PLOT_TYPE = ".svg"
HTML_INDEX_FILE = 'index.html'
DOC_URL = 'http://spec2nexus.readthedocs.io/en/latest/specplot_gallery.html'


class DirectoryNotFoundError(ValueError): 
    """Exception: The requested directory does not exist"""

class PathIsNotDirectoryError(ValueError): 
    """Exception: The path is not a directory"""


class PlotSpecFileScans(object):
    
    """
    read a SPEC data file and plot thumbnail images of all its scans
    
    :param [str] filelist: list of SPEC data files to be checked
    :param str plotDir: name of base directory to store output image thumbnails

    .. autosummary::
    
        ~specFileUpdated
        ~plot_all_scans
        ~getPlotDir
        ~getBaseDir
        ~href_format

    """

    def __init__(self, filelist, plotDir = None, reverse_chronological = False):
        self.filelist = filelist
        self.plotDir = plotDir or os.getcwd()
        self.reversed = reverse_chronological

        for specFile in filelist:
            self.plot_all_scans(specFile)
    
    def specFileUpdated(self, specFile):
        """
        report if specFile has been updated
        
        Return mtime cache entry (or `None` if not updated)
        """
        result = None
        if os.path.exists(specFile):
            mtime_cache = Cache_File_Mtime(self.plotDir)
            if mtime_cache.was_file_updated(specFile):
                result = mtime_cache.get(specFile)
        return result
    
    def plot_all_scans(self, specFile):
        """
        plot all the recognized scans from the file named ``specFile``
        """
        if not spec.is_spec_file(specFile):
            raise spec.NotASpecDataFile(specFile)

        last_cache = Cache_File_Mtime(self.plotDir).get(specFile)
        cache = self.specFileUpdated(specFile)
        if cache is None:
            return

        try:
            logger("SPEC data file: %s" % specFile)
            sd = specplot.openSpecFile(specFile)
        except FileNotFoundError:
            return    # could not open file, be silent about it
        if len(sd.headers) == 0:    # no scan header found, again, silence
            return

        plot_path = self.getPlotDir(specFile)
        logger("  plot directory: %s" % plot_path)
        if not os.path.exists(plot_path):
            os.makedirs(plot_path)
            logger('creating directory: ' + plot_path)
        plot_list = [
            k
            for k in sorted(os.listdir(plot_path))
            if k.endswith(PLOT_TYPE)
            ]
        
        # check if any plots need to be removed (and remade)
        if len(plot_list) > 0 and cache["size"] > 0 and cache["size"] != last_cache["size"]:
            if cache["size"] > last_cache["size"]:
                # Was last scan updated with more data?  Look at file.
                with open(specFile, "r") as fp:
                    # skip the part already considered
                    fp.read(last_cache["size"])
                    # look at the addition
                    buf = fp.read()

                # only delete last plot if addition not start with #S
                if not buf.lstrip().startswith("#S "):
                    k = plot_list.pop()
                    os.remove(os.path.join(plot_path, k))
            else:
                # remake all the plots
                for k in plot_list:     # TODO: needs unit test
                    os.remove(os.path.join(plot_path, k))
                plot_list = []
    
        problem_scans = []
        newFileList = [] # list of all new files created
        
        shutil.copy(specFile, plot_path)
        
        scan_list = sd.getScanNumbers()
        if self.reversed:
            scan_list = reversed(sd.getScanNumbersChronological())

        for scan_number in scan_list:
            scan = sd.getScan(scan_number)
            # make certain that plot files will sort lexically:  S1 --> s00001
            base = 's%05s' + PLOT_TYPE
            basePlotFile = (base % str(scan.scanNum)).replace(' ', '0')
            fullPlotFile = os.path.join(plot_path, basePlotFile)
            altText = '#' + str(scan.scanNum) + ': ' + scan.scanCmd
            href = self.href_format(basePlotFile, altText)

            if basePlotFile in plot_list:
                newFileList.append(fullPlotFile)
                continue
            
            #print ("specplot.py %s %s %s" % (specFile, scan.scanNum, fullPlotFile))
            if needToMakePlot(fullPlotFile, cache["mtime"]):
                try:
                    logger('  creating SPEC data scan image: ' + basePlotFile)
                    selector = specplot.Selector()
                    image_maker = selector.auto(scan)
                    plotter = image_maker()
                    plotter.plot_scan(scan, fullPlotFile)
                    newFileList.append(fullPlotFile)
                    plot_list.append(href)
                except Exception as _exc_obj:
                    msg = "<b>%s</b>" % type(_exc_obj).__name__
                    msg += ": <tt>#S %s</tt>" % str(scan)
                    #msg += " (%s)" % specFile
                    problem_scans.append(msg)
    
        htmlFile = os.path.join(plot_path, HTML_INDEX_FILE)
        if len(newFileList) or not os.path.exists(htmlFile):
            logger('  creating/updating index.html file')
            html = buildIndexHtml(specFile, plot_list, problem_scans)
            f = open(htmlFile, "w")
            f.write(html)
            f.close()
            newFileList.append(htmlFile)
            
        # touch to update the mtime on the plot_path
        os.utime(plot_path, None)
    
    def getPlotDir(self, specFile):
        """
        return the plot directory based on the specFile
        
        :param str specFile: name of SPEC data file (relative or absolute)
        """
        data_file_root_name = os.path.splitext(os.path.split(specFile)[1])[0]
        date_str = getSpecFileDate(specFile)
        if date_str is None:
            return
        return self.getBaseDir(data_file_root_name, date_str)

    def getBaseDir(self, basename, date):
        """
        find the path based on the date in the spec file
        """
        return os.path.join(self.plotDir, datePath(date), basename)
    
    def href_format(self, basePlotFile, altText):
        href = '<a href="' + basePlotFile + '">'
        href += '<img src="' + basePlotFile + '"'
        href += ' width="150" height="75"'
        href += ' alt="' + altText + '"/>'
        href += '</a>'
        return href


class Cache_File_Mtime(object):
    
    """
    maintain a list of all known data file modification times
    
    :param str base_dir: name of base directory to store output image thumbnails
    
    This list will allow the code to avoid unnecessary work
    reparsing and plotting of unchanged SPEC data files.
    """

    def __init__(self, base_dir):
        if not os.path.exists(base_dir):
            msg = 'directory does not exist: ' + base_dir
            raise DirectoryNotFoundError(msg)
        self.base_dir = os.path.abspath(base_dir)
        self.cache_file = os.path.join(self.base_dir, MTIME_CACHE_FILE)
        self.cache = self.read()

    def read(self):
        """read the cache from storage"""
        cache = {}
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as fp:
                cache = json.load(fp)
        return cache

    def write(self):
        """write the cache to storage"""
        with open(self.cache_file, 'w') as fp:
            json.dump(self.cache, fp, indent=4)
    
    def get(self, fname, default=dict(mtime=0, size=0)):
        """
        get the mtime cache entry for data file ``fname``
         
        :param str fname: file name, already known to exist
        :return: time (float) cached value of when fname was 
            last modified or None if not known
        """
        return self.cache.get(fname, default)
        
    def was_file_updated(self, fname):
        """
        compare the mtime between disk and cache
        
        :param str fname: file name, already known to exist
        :return bool: True if file is newer than the cache (or new to the cache)
        """
        assert os.path.exists(fname)
        updated = False
        cache = self.get(fname)
        
        file_mtime = os.path.getmtime(fname)
        file_size = os.path.getsize(fname)

        if file_mtime != cache["mtime"] and file_size != cache["size"]:
            updated = True

        if updated:
            logger('SPEC data file updated: ' + fname)
            self.cache[fname] = dict(mtime=file_mtime, size=os.path.getsize(fname))
            self.write()
        return updated

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def datePath(date):
    """
    convert the date into a path: yyyy/mm
    
    :param str date: text date from SPEC file #D line: 'Thu Jun 19 12:21:55 2014'
    """
    import time
    dateStr = time.strptime(date, "%a %b %d %H:%M:%S %Y")
    yyyy = "%04d" % dateStr.tm_year
    mm = "%02d" % dateStr.tm_mon
    return os.path.join(yyyy, mm)


def getSpecFileDate(specFile):
    """
    return the #D date of the SPEC data file or None
    
    :param str specFile: name of SPEC data file (relative or absolute)
    """
    # Get that without parsing the data file, it's on the 3rd line of the file.
    #     #F 06_19_Tony.dat
    #     #E 1403198515
    #     #D Thu Jun 19 12:21:55 2014
    if not os.path.exists(specFile):
        return None

    # read the first lines of the file and validate for SPEC data file format
    f = open(specFile, 'r')
    line = f.readline()
    if not line.startswith('#F '): return None
    line = f.readline()
    if not line.startswith('#E '): return None
    line = f.readline()
    if not line.startswith('#D '): return None
    f.close()

    return line[2:].strip()  # 'Thu Jun 19 12:21:55 2014'


def needToMakePlot(fullPlotFile, mtime_specFile):
    """
    Determine if a plot needs to be (re)made.  Use mtime as the basis.

    :return bool: ``True`` if plot should be made again
    """
    remake_plot = True
    if os.path.exists(fullPlotFile):
        mtime_plotFile = os.path.getmtime(fullPlotFile)
        if mtime_plotFile > mtime_specFile:
            # plot was made after the data file was updated
            remake_plot = False     # don't remake the plot
    return remake_plot


def timestamp():
    """
    current time as yyyy-mm-dd hh:mm:ss
    
    :return str: 
    """
    ts = str(datetime.datetime.now())
    ts = ' '.join(ts.split('T'))    # convert to modified ISO8601 format
    ts = ts.split('.')[0]           # strip off the fractional seconds
    return ts


def buildIndexHtml(specFile, plotted_scans, problem_scans):
    """
    build index.html content
    
    :param str specFile: name of SPEC data file (relative or absolute)
    :param [str] plotList: list of HTML `<a>` elements, one for each plot image 
    """
    baseSpecFile = os.path.basename(specFile)
    comment = "\n"
    comment += "   written by: %s\n" % sys.argv[0]
    comment += "   date: %s\n"       % timestamp()
    comment += "\n"

    href = "<a href='%s'>%s</a>" % (baseSpecFile, specFile)
    html  = "<html>\n"
    html += "  <head>\n"
    html += "    <title>SPEC scans from %s</title>\n" % os.path.split(specFile)[-1]
    html += "    <!-- %s -->\n"                       % comment
    html += "  </head>\n"
    html += "  <body>\n"
    html += "    <h1>SPEC scans from: %s</h1>\n"      % os.path.split(specFile)[-1]
    html += "\n"
    html += "    spec file: %s\n"                     % href
    html += "    <br />\n"
    html += "\n"
    if len(problem_scans) > 0:
        html += "    <h2>%d scan(s) with plotting problems</h2>\n" % len(problem_scans)
        html += "\n"
        html += "    <ul>\n"
        for item in problem_scans:
            html += "    <li>%s</li>\n" % item
        html += "    </ul>\n"
    html += "\n"
    html += "    <h2>%d plotted scan(s)</h2>\n" % len(plotted_scans)
    html += "\n"
    html += "\n".join(plotted_scans)
    html += "\n"
    html += "\n"
    html += "    <hr />\n"
    ref = 'page created: ' + str(datetime.datetime.now())
    ref += ', specplot_gallery documentation: <a href="%s">%s</a>' % (DOC_URL, DOC_URL)
    html += "    <center><small>%s</small></center>\n" % ref
    html += "\n"
    html += "  </body>\n"
    html += "</html>\n"
    return html


def logger(message):
    """
    log a message or report from this module

    :param str message: text to be logged
    """
    now = str(datetime.datetime.now())
    name = os.path.basename(sys.argv[0])
    pid = os.getpid()
    text = "(%d,%s,%s) %s" % (pid, name, now, message)
    logging.info(text)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def main():
    import argparse
    global SPECPLOTS_DIR

    doc = __doc__.strip().splitlines()[0]
    p = argparse.ArgumentParser(description=doc)
    
    p.add_argument(
        'paths',  
        nargs='+',  
        help="SPEC data file name(s) or directory(s) with SPEC data files")
    
    p.add_argument(
        '-r', 
        action='store_true', 
        default=False,
        dest='reverse_chronological',
        help='sort images from each data file in reverse chronolgical order')

    pwd = os.getcwd()
    msg = 'base directory for output'
    msg += ' (default:' + pwd + ')'
    p.add_argument('-d', '--dir', help=msg)

    args = p.parse_args()

    specplots_dir = args.dir or pwd
    if not os.path.exists(specplots_dir):
        raise DirectoryNotFoundError(specplots_dir)
    if not os.path.isdir(specplots_dir):
        raise PathIsNotDirectoryError(specplots_dir)
    
    file_list = []

    def only_accept_spec_files(fname):
        if os.path.exists(fname) and spec.is_spec_file(fname):
            file_list.append(fname)

    for item in args.paths:
        if os.path.exists(item):
            if os.path.isfile(item):
                only_accept_spec_files(item)
            elif os.path.isdir(item):
                for subitem in os.listdir(item):
                    only_accept_spec_files(os.path.join(item, subitem))

    log_file = os.path.join(specplots_dir, 'specplot_files_processing.log')
    logging.basicConfig(filename=log_file, level=logging.INFO)

    logger('>'*10 + ' starting')
    # TODO: do not start this process if it is running from previous call
    PlotSpecFileScans(
        file_list, 
        specplots_dir, 
        reverse_chronological=args.reverse_chronological)
    logger('<'*10 + ' finished')


def developer():
    """
    supply a file and a directory as command-line arguments to "paths"
    """
    import tempfile
    
    tempdir = tempfile.mkdtemp()
    sys.argv.append('-d')
    sys.argv.append(tempdir)
    sys.argv.append(os.path.join('data', '02_03_setup.dat'))
    sys.argv.append(os.path.join('..', '..', 'tests','data'))
    main()
    logging.disable(logging.CRITICAL)
    logging.shutdown()
    shutil.rmtree(tempdir)
    logging.disable(logging.NOTSET)


if __name__ == '__main__':
    main()
    # developer()
