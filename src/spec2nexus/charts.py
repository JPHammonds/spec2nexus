#!/usr/bin/env python

'''
charting for spec2nexus

.. autosummary::

    ~make_png
    ~xy_plot

'''

import datetime
import numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


SCALING_FACTOR = 1        #  2**24
PLOT_H_INT = 7
PLOT_V_INT = 3
COLORMAP = 'cubehelix'        # http://matplotlib.org/api/pyplot_summary.html#matplotlib.pyplot.colormaps

# MatPlotLib advises to re-use the figure() object rather create new ones
# http://stackoverflow.com/questions/21884271/warning-about-too-many-open-figures
MPL_FIG = None


def make_png(
        image, 
        imgfile, 
        axes = None,
        title = '2-D data',
        subtitle = '',
        log_image=False, 
        hsize=PLOT_H_INT, 
        vsize=PLOT_V_INT, 
        cmap=COLORMAP,
        xtitle=None, ytitle=None, 
        timestamp_str=None):
    '''
    read the image from the named HDF5 file and make a PNG file
    
    Test that the HDF5 file exists and that the path to the data exists in that file.
    Read the data from the named dataset, mask off some bad values, 
    convert to log(image) and use Matplotlib to make the PNG file.
    
    The HDF5 file could be a NeXus file, not required though.
    
    :param obj image: array of data to be rendered
    :param str imgfile: name of image file to be written (path is optional)
    :param bool log_image: plot log(image)
    :param int hsize: horizontal size of the PNG image (default: 7)
    :param int hsize: vertical size of the PNG image (default: 3)
    :param str cmap: colormap for the image (default: 'cubehelix'), 'jet' is another good one
    :return str: *imgfile*
    '''

    # replace masked data with min good value
    image_data = numpy.ma.masked_less_equal(image, 0)
    image_data = image_data.filled(image_data.min())
    if log_image and image_data.max() != 0:     # apply log scaling
        image_data = numpy.log(image_data)
        image_data -= image_data.min()
        image_data *= SCALING_FACTOR / image_data.max()

    fig = matplotlib.figure.Figure(figsize=(9, 5))
    fig.clf()
    ax = fig.add_subplot('111')
    # TODO: apply axes scaling
    ax.imshow(image_data, interpolation='nearest')

    timestamp_str = timestamp_str or str(datetime.datetime.now())
    
    ax.set_title(subtitle, fontsize=9)
    fig.suptitle(title, fontsize=10)
    fig.text(0.02, 0., timestamp_str,
        fontsize=8, color='gray',
        ha='left', va='bottom', alpha=0.5)

    FigureCanvas(fig).print_figure(imgfile, bbox_inches='tight')

    return imgfile


def xy_plot(x, y, 
              plotfile, 
              title=None, subtitle=None, 
              xtitle=None, ytitle=None, 
              xlog=False, ylog=False,
              timestamp_str=None):
    r'''
    with MatPlotLib, generate a plot of a scan (as if data from a scan in a SPEC file)
    
    :param [float] x: horizontal axis data
    :param [float] y: vertical axis data
    :param str plotfile: file name to write plot image
    :param str xtitle: horizontal axis label (default: not shown)
    :param str ytitle: vertical axis label (default: not shown)
    :param str title: title for plot (default: date time)
    :param str subtitle: subtitle for plot (default: not shown)
    :param bool xlog: should X axis be log (default: False=linear)
    :param bool ylog: should Y axis be log (default: False=linear)
    :param str timestamp_str: date to use on plot (default: now)

    .. tip:: when using this module as a background task ...
    
        MatPlotLib has several interfaces for plotting. 
        Since this module runs as part of a background job 
        generating lots of plots, MatPlotLib's standard ``plt`` code is 
        not the right model.  It warns after 20 plots and 
        will eventually run out of memory.  
        
        Here's the fix used in this module:
        http://stackoverflow.com/questions/16334588/create-a-figure-that-is-reference-counted/16337909#16337909

    '''
    fig = matplotlib.figure.Figure(figsize=(9, 5))
    fig.clf()

    ax = fig.add_subplot('111')
    if xlog:
        ax.set_xscale('log')
        if max(x) <= 0:
            msg = 'X data has no positive values,'
            msg += ' and therefore can not be log-scaled.'
            raise ValueError(msg)
    if ylog:
        ax.set_yscale('log')
        if max(y) <= 0:
            msg = 'Y data has no positive values,'
            msg += ' and therefore can not be log-scaled.'
            raise ValueError(msg)
    if not xlog and not ylog:
        ax.ticklabel_format(useOffset=False)
    if xtitle is not None:
        ax.set_xlabel(xtitle)
    if ytitle is not None:
        ax.set_ylabel(ytitle)

    if subtitle is not None:
        ax.set_title(subtitle, fontsize=9)

    timestamp_str = timestamp_str or str(datetime.datetime.now())
    if title is None:
        title = timestamp_str
    else:
        fig.text(0.02, 0., timestamp_str,
            fontsize=8, color='gray',
            ha='left', va='bottom', alpha=0.5)
    fig.suptitle(title, fontsize=10)

    ax.plot(x, y, 'o-')

    FigureCanvas(fig).print_figure(plotfile, bbox_inches='tight')
