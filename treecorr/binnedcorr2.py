# Copyright (c) 2003-2019 by Mike Jarvis
#
# TreeCorr is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.

"""
.. module:: binnedcorr2
"""

import math
import numpy as np
import sys
import coord
import treecorr

class Namespace(object):
    pass

class BinnedCorr2(object):
    """This class stores the results of a 2-point correlation calculation, along with some
    ancillary data.

    This is a base class that is not intended to be constructed directly.  But it has a few
    helper functions that derived classes can use to help perform their calculations.  See
    the derived classes for more details:

    - `GGCorrelation` handles shear-shear correlation functions
    - `NNCorrelation` handles count-count correlation functions
    - `KKCorrelation` handles kappa-kappa correlation functions
    - `NGCorrelation` handles count-shear correlation functions
    - `NKCorrelation` handles count-kappa correlation functions
    - `KGCorrelation` handles kappa-shear correlation functions

    .. note::

        When we refer to kappa in the correlation functions, that is because TreeCorr was
        originally designed for weak lensing applications.  But in fact any scalar quantity
        may be used here.  CMB temperature fluctuations for example.

    The constructor for all derived classes take a config dict as the first argument,
    since this is often how we keep track of parameters, but if you don't want to
    use one or if you want to change some parameters from what are in a config dict,
    then you can use normal kwargs, which take precedence over anything in the config dict.

    There are a number of possible definitions for the distance between two points, which
    are appropriate for different use cases.  These are specified by the ``metric`` parameter.
    The possible options are:

        - 'Euclidean' = straight line Euclidean distance between two points.
        - 'FisherRperp' = the perpendicular component of the distance, following the
          definitions in Fisher et al, 1994 (MNRAS, 267, 927).
        - 'OldRperp' = the perpendicular component of the distance using the definition
          of Rperp from TreeCorr v3.x.
        - 'Rperp' = an alias for FisherRperp.  You can change it to be an alias for
          OldRperp if you want by setting ``treecorr.Rperp_alias = 'OldRperp'`` before
          using it.
        - 'Rlens' = the distance from the first object (taken to be a lens) to the line
          connecting Earth and the second object (taken to be a lensed source).
        - 'Arc' = the true great circle distance for spherical coordinates.
        - 'Periodic' = Like Euclidean, but with periodic boundaries.

    See `Metrics` for more information about these various metric options.

    There are also a few different possibile binning prescriptions to define the range of
    distances, which should be placed into each bin.

        - 'Log' - logarithmic binning in the distance.  The bin steps will be uniform in
          log(r) from log(min_sep) .. log(max_sep).
        - 'Linear' - linear binning in the distance.  The bin steps will be uniform in r
          from min_sep .. max_sep.
        - 'TwoD' = 2-dimensional binning from x = (-max_sep .. max_sep) and
          y = (-max_sep .. max_sep).  The bin steps will be uniform in both x and y.
          (i.e. linear in x,y)

    See `Binning` for more information about the different binning options.

    Parameters:
        config (dict):      A configuration dict that can be used to pass in the below kwargs if
                            desired.  This dict is allowed to have addition entries in addition
                            to those listed below, which are ignored here. (default: None)
        logger:             If desired, a logger object for logging. (default: None, in which case
                            one will be built according to the config dict's verbose level.)

    Keyword Arguments:

        nbins (int):        How many bins to use. (Exactly three of nbins, bin_size, min_sep,
                            max_sep are required. If nbins is not given, it will be calculated from
                            the values of the other three, rounding up to the next highest integer.
                            In this case, bin_size will be readjusted to account for this rounding
                            up.)
        bin_size (float):   The width of the bins in log(separation). (Exactly three of nbins,
                            bin_size, min_sep, max_sep are required.  If bin_size is not given, it
                            will be calculated from the values of the other three.)
        min_sep (float):    The minimum separation in units of sep_units, if relevant. (Exactly
                            three of nbins, bin_size, min_sep, max_sep are required.  If min_sep is
                            not given, it will be calculated from the values of the other three.)
        max_sep (float):    The maximum separation in units of sep_units, if relevant. (Exactly
                            three of nbins, bin_size, min_sep, max_sep are required.  If max_sep is
                            not given, it will be calculated from the values of the other three.

        sep_units (str):    The units to use for the separation values, given as a string.  This
                            includes both min_sep and max_sep above, as well as the units of the
                            output distance values.  Valid options are arcsec, arcmin, degrees,
                            hours, radians.  (default: radians if angular units make sense, but for
                            3-d or flat 2-d positions, the default will just match the units of
                            x,y[,z] coordinates)
        bin_slop (float):   How much slop to allow in the placement of pairs in the bins.
                            If bin_slop = 1, then the bin into which a particular pair is placed
                            may be incorrect by at most 1.0 bin widths.  (default: None, which
                            means to use a bin_slop that gives a maximum error of 10% on any bin,
                            which has been found to yield good results for most application.
        brute (bool):       Whether to use the "brute force" algorithm.  (default: False) Options
                            are:

                             - False (the default): Stop at non-leaf cells whenever the error in
                               the separation is compatible with the given bin_slop.
                             - True: Go to the leaves for both catalogs.
                             - 1: Always go to the leaves for cat1, but stop at non-leaf cells of
                               cat2 when the error is compatible with the given bin_slop.
                             - 2: Always go to the leaves for cat2, but stop at non-leaf cells of
                               cat1 when the error is compatible with the given bin_slop.

        verbose (int):      If no logger is provided, this will optionally specify a logging level
                            to use:

                             - 0 means no logging output
                             - 1 means to output warnings only (default)
                             - 2 means to output various progress information
                             - 3 means to output extensive debugging information

        log_file (str):     If no logger is provided, this will specify a file to write the logging
                            output.  (default: None; i.e. output to standard output)
        output_dots (bool): Whether to output progress dots during the calcualtion of the
                            correlation function. (default: False unless verbose is given and >= 2,
                            in which case True)

        split_method (str): How to split the cells in the tree when building the tree structure.
                            Options are:

                            - mean = Use the arithmetic mean of the coordinate being split.
                              (default)
                            - median = Use the median of the coordinate being split.
                            - middle = Use the middle of the range; i.e. the average of the minimum
                              and maximum value.
                            - random: Use a random point somewhere in the middle two quartiles of
                              the range.

        min_top (int):      The minimum number of top layers to use when setting up the field.
                            (default: :math:`\\max(3, \\log_2(N_{\\rm cpu}))`)
        max_top (int):      The maximum number of top layers to use when setting up the field.
                            The top-level cells are where each calculation job starts. There will
                            typically be of order :math:`2^{\\rm max\\_top}` top-level cells.
                            (default: 10)
        precision (int):    The precision to use for the output values. This specifies how many
                            digits to write. (default: 4)
        pairwise (bool):    Whether to use a different kind of calculation for cross correlations
                            whereby corresponding items in the two catalogs are correlated pairwise
                            rather than the usual case of every item in one catalog being correlated
                            with every item in the other catalog. (default: False) (DEPRECATED)
        m2_uform (str):     The default functional form to use for aperture mass calculations.
                            see `calculateMapSq` for more details.  (default: 'Crittenden')

        metric (str):       Which metric to use for distance measurements.  Options are listed
                            above.  (default: 'Euclidean')
        bin_type (str):     What type of binning should be used.  Options are listed above.
                            (default: 'Log')
        min_rpar (float):   For any metric that supports it, the minimum difference in Rparallel
                            to allow for pairs being included in the correlation function.
                            (default: None)
        max_rpar (float):   For any metric that supports it,, the maximum difference in Rparallel
                            to allow for pairs being included in the correlation function.
                            (default: None)
        period (float):     For the 'Periodic' metric, the period to use in all directions.
                            (default: None)
        xperiod (float):    For the 'Periodic' metric, the period to use in the x direction.
                            (default: period)
        yperiod (float):    For the 'Periodic' metric, the period to use in the y direction.
                            (default: period)
        zperiod (float):    For the 'Periodic' metric, the period to use in the z direction.
                            (default: period)

        var_method (str):   Which method to use for estimating the variance. Options are:
                            'shot', 'jackknife', 'sample', 'bootstrap', 'marked_bootstrap'.
                            (default: 'shot')
        num_bootstrap (int): How many bootstrap samples to use for the 'bootstrap' and
                            'marked_bootstrap' var_methods.  (default: 500)

        num_threads (int):  How many OpenMP threads to use during the calculation.
                            (default: use the number of cpu cores)

                            .. note::

                                This won't work if the system's C compiler cannot use OpenMP
                                (e.g. clang prior to version 3.7.)
    """
    _valid_params = {
        'nbins' : (int, False, None, None,
                'The number of output bins to use.'),
        'bin_size' : (float, False, None, None,
                'The size of the output bins in log(sep).'),
        'min_sep' : (float, False, None, None,
                'The minimum separation to include in the output.'),
        'max_sep' : (float, False, None, None,
                'The maximum separation to include in the output.'),
        'sep_units' : (str, False, None, coord.AngleUnit.valid_names,
                'The units to use for min_sep and max_sep.  '
                'Also the units of the output distances'),
        'bin_slop' : (float, False, None, None,
                'The fraction of a bin width by which it is ok to let the pairs miss the correct '
                'bin.',
                'The default is to use 1 if bin_size <= 0.1, or 0.1/bin_size if bin_size > 0.1.'),
        'brute' : (bool, False, False, [False, True, 1, 2],
                'Whether to use brute-force algorithm'),
        'verbose' : (int, False, 1, [0, 1, 2, 3],
                'How verbose the code should be during processing. ',
                '0 = Errors Only, 1 = Warnings, 2 = Progress, 3 = Debugging'),
        'log_file' : (str, False, None, None,
                'If desired, an output file for the logging output.',
                'The default is to write the output to stdout.'),
        'output_dots' : (bool, False, None, None,
                'Whether to output dots to the stdout during the C++-level computation.',
                'The default is True if verbose >= 2 and there is no log_file.  Else False.'),
        'split_method' : (str, False, 'mean', ['mean', 'median', 'middle', 'random'],
                'Which method to use for splitting cells.'),
        'min_top' : (int, False, None, None,
                'The minimum number of top layers to use when setting up the field.'),
        'max_top' : (int, False, 10, None,
                'The maximum number of top layers to use when setting up the field.'),
        'precision' : (int, False, 4, None,
                'The number of digits after the decimal in the output.'),
        'pairwise' : (bool, True, False, None,
                'Whether to do a pair-wise cross-correlation. (DEPRECATED)'),
        'm2_uform' : (str, False, 'Crittenden', ['Crittenden', 'Schneider'],
                'The function form of the mass aperture.'),
        'metric': (str, False, 'Euclidean', ['Euclidean', 'Rperp', 'FisherRperp', 'OldRperp',
                                             'Rlens', 'Arc', 'Periodic'],
                'Which metric to use for the distance measurements'),
        'bin_type': (str, False, 'Log', ['Log', 'Linear', 'TwoD'],
                'Which type of binning should be used'),
        'min_rpar': (float, False, None, None,
                'The minimum difference in Rparallel for pairs to include'),
        'max_rpar': (float, False, None, None,
                'The maximum difference in Rparallel for pairs to include'),
        'period': (float, False, None, None,
                'The period to use for all directions for the Periodic metric'),
        'xperiod': (float, False, None, None,
                'The period to use for the x direction for the Periodic metric'),
        'yperiod': (float, False, None, None,
                'The period to use for the y direction for the Periodic metric'),
        'zperiod': (float, False, None, None,
                'The period to use for the z direction for the Periodic metric'),

        'var_method': (str, False, 'shot',
                ['shot', 'jackknife', 'sample', 'bootstrap', 'marked_bootstrap'],
                'The method to use for estimating the variance'),
        'num_bootstrap': (int, False, 500, None,
                'How many bootstrap samples to use for the var_method=bootstrap and '
                'marked_bootstrap'),
        'num_threads' : (int, False, None, None,
                'How many threads should be used. num_threads <= 0 means auto based on num cores.'),
    }

    def __init__(self, config=None, logger=None, **kwargs):
        self._corr = None  # Do this first to make sure we always have it for __del__
        self.config = treecorr.config.merge_config(config,kwargs,BinnedCorr2._valid_params)
        if logger is None:
            self.logger = treecorr.config.setup_logger(
                    treecorr.config.get(self.config,'verbose',int,1),
                    self.config.get('log_file',None))
        else:
            self.logger = logger

        # We'll make a bunch of attributes here, which we put into a namespace called _ro.
        # These are the core attributes that won't ever be changed after construction.
        # This is an efficiency optimization (both memory and flops), since it will allow
        # copy() to just copy a pointer to the _ro namespace without having to copy each
        # individual attribute separately.
        # The access of these attributes are all via read-only properties.
        self._ro = Namespace()

        if 'output_dots' in self.config:
            self._ro.output_dots = treecorr.config.get(self.config,'output_dots',bool)
        else:
            self._ro.output_dots = treecorr.config.get(self.config,'verbose',int,1) >= 2

        self._ro.bin_type = self.config.get('bin_type', None)

        self._ro.sep_units = self.config.get('sep_units','')
        self._ro._sep_units = treecorr.config.get(self.config,'sep_units',str,'radians')
        self._ro._log_sep_units = math.log(self._sep_units)
        if 'nbins' not in self.config:
            if 'max_sep' not in self.config:
                raise TypeError("Missing required parameter max_sep")
            if 'min_sep' not in self.config and self.bin_type != 'TwoD':
                raise TypeError("Missing required parameter min_sep")
            if 'bin_size' not in self.config:
                raise TypeError("Missing required parameter bin_size")
            self._ro.min_sep = float(self.config.get('min_sep',0))
            self._ro.max_sep = float(self.config['max_sep'])
            if self.min_sep >= self.max_sep:
                raise ValueError("max_sep must be larger than min_sep")
            self._ro.bin_size = float(self.config['bin_size'])
            self._ro.nbins = None
        elif 'bin_size' not in self.config:
            if 'max_sep' not in self.config:
                raise TypeError("Missing required parameter max_sep")
            if 'min_sep' not in self.config and self.bin_type != 'TwoD':
                raise TypeError("Missing required parameter min_sep")
            self._ro.min_sep = float(self.config.get('min_sep',0))
            self._ro.max_sep = float(self.config['max_sep'])
            if self.min_sep >= self.max_sep:
                raise ValueError("max_sep must be larger than min_sep")
            self._ro.nbins = int(self.config['nbins'])
            self._ro.bin_size = None
        elif 'max_sep' not in self.config:
            if 'min_sep' not in self.config and self.bin_type != 'TwoD':
                raise TypeError("Missing required parameter min_sep")
            self._ro.min_sep = float(self.config.get('min_sep',0))
            self._ro.nbins = int(self.config['nbins'])
            self._ro.bin_size = float(self.config['bin_size'])
            self._ro.max_sep = None
        else:
            if self.bin_type == 'TwoD':
                raise TypeError("Only 2 of max_sep, bin_size, nbins are allowed "
                                "for bin_type='TwoD'.")
            if 'min_sep' in self.config:
                raise TypeError("Only 3 of min_sep, max_sep, bin_size, nbins are allowed.")
            self._ro.max_sep = float(self.config['max_sep'])
            self._ro.nbins = int(self.config['nbins'])
            self._ro.bin_size = float(self.config['bin_size'])
            self._ro.min_sep = None

        if self.bin_type == 'Log':
            if self.nbins is None:
                self._ro.nbins = int(math.ceil(math.log(self.max_sep/self.min_sep)/self.bin_size))
                # Update bin_size given this value of nbins
                self._ro.bin_size = math.log(self.max_sep/self.min_sep)/self.nbins
            elif self.bin_size is None:
                self._ro.bin_size = math.log(self.max_sep/self.min_sep)/self.nbins
            elif self.max_sep is None:
                self._ro.max_sep = math.exp(self.nbins*self.bin_size)*self.min_sep
            else:
                self._ro.min_sep = self.max_sep*math.exp(-self.nbins*self.bin_size)

            # This makes nbins evenly spaced entries in log(r) starting with 0 with step bin_size
            self._ro.logr = np.linspace(0, self.nbins*self.bin_size, self.nbins, endpoint=False,
                                          dtype=float)
            # Offset by the position of the center of the first bin.
            self._ro.logr += math.log(self.min_sep) + 0.5*self.bin_size
            self._ro.rnom = np.exp(self.logr)
            half_bin = np.exp(0.5*self.bin_size)
            self._ro.left_edges = self.rnom / half_bin
            self._ro.right_edges = self.rnom * half_bin
            self._ro._nbins = self.nbins
            self._ro._bintype = treecorr._lib.Log
            min_log_bin_size = self.bin_size
            max_log_bin_size = self.bin_size
            max_good_slop = 0.1 / self.bin_size
        elif self.bin_type == 'Linear':
            if self.nbins is None:
                self._ro.nbins = int(math.ceil((self.max_sep-self.min_sep)/self.bin_size))
                # Update bin_size given this value of nbins
                self._ro.bin_size = (self.max_sep-self.min_sep)/self.nbins
            elif self.bin_size is None:
                self._ro.bin_size = (self.max_sep-self.min_sep)/self.nbins
            elif self.max_sep is None:
                self._ro.max_sep = self.min_sep + self.nbins*self.bin_size
            else:
                self._ro.min_sep = self.max_sep - self.nbins*self.bin_size

            self._ro.rnom = np.linspace(self.min_sep, self.max_sep, self.nbins, endpoint=False,
                                          dtype=float)
            # Offset by the position of the center of the first bin.
            self._ro.rnom += 0.5*self.bin_size
            self._ro.left_edges = self.rnom - 0.5*self.bin_size
            self._ro.right_edges = self.rnom + 0.5*self.bin_size
            self._ro.logr = np.log(self.rnom)
            self._ro._nbins = self.nbins
            self._ro._bintype = treecorr._lib.Linear
            min_log_bin_size = self.bin_size / self.max_sep
            max_log_bin_size = self.bin_size / (self.min_sep + self.bin_size/2)
            max_good_slop = 0.1 / max_log_bin_size
        elif self.bin_type == 'TwoD':
            if self.nbins is None:
                self._ro.nbins = int(math.ceil(2.*self.max_sep / self.bin_size))
                self._ro.bin_size = 2.*self.max_sep/self.nbins
            elif self.bin_size is None:
                self._ro.bin_size = 2.*self.max_sep/self.nbins
            else:
                self._ro.max_sep = self.nbins * self.bin_size / 2.

            sep = np.linspace(-self.max_sep, self.max_sep, self.nbins, endpoint=False,
                              dtype=float)
            sep += 0.5 * self.bin_size
            dx, dy = np.meshgrid(sep, sep)
            self._ro.left_edges = dx - 0.5*self.bin_size
            self._ro.right_edges = dx + 0.5*self.bin_size
            self._ro.bottom_edges = dy - 0.5*self.bin_size
            self._ro.top_edges = dy + 0.5*self.bin_size
            self._ro.rnom = np.sqrt(dx**2 + dy**2)
            self._ro.logr = np.zeros_like(self.rnom)
            np.log(self.rnom, out=self._ro.logr, where=self.rnom > 0)
            self._ro.logr[self.rnom==0.] = -np.inf
            self._ro._nbins = self.nbins**2
            self._ro._bintype = treecorr._lib.TwoD
            min_log_bin_size = self.bin_size / self.max_sep
            max_log_bin_size = self.bin_size / (self.min_sep + self.bin_size/2)
            max_good_slop = 0.1 / max_log_bin_size
        else:  # pragma: no cover  (Already checked by config layer)
            raise ValueError("Invalid bin_type %s"%self.bin_type)

        if self.sep_units == '':
            self.logger.info("nbins = %d, min,max sep = %g..%g, bin_size = %g",
                             self.nbins, self.min_sep, self.max_sep, self.bin_size)
        else:
            self.logger.info("nbins = %d, min,max sep = %g..%g %s, bin_size = %g",
                             self.nbins, self.min_sep, self.max_sep, self.sep_units,
                             self.bin_size)
        # The underscore-prefixed names are in natural units (radians for angles)
        self._ro._min_sep = self.min_sep * self._sep_units
        self._ro._max_sep = self.max_sep * self._sep_units
        if self.bin_type in ['Linear', 'TwoD']:
            self._ro._bin_size = self.bin_size * self._sep_units
            min_log_bin_size *= self._sep_units
        else:
            self._ro._bin_size = self.bin_size

        self._ro.split_method = self.config.get('split_method','mean')
        self.logger.debug("Using split_method = %s",self.split_method)

        self._ro.min_top = treecorr.config.get(self.config,'min_top',int,None)
        self._ro.max_top = treecorr.config.get(self.config,'max_top',int,10)

        self._ro.bin_slop = treecorr.config.get(self.config,'bin_slop',float,-1.0)
        if self.bin_slop < 0.0:
            self._ro.bin_slop = min(max_good_slop, 1.0)
        self._ro.b = min_log_bin_size * self.bin_slop
        if self.bin_slop > max_good_slop + 0.0001:  # Add some numerical slop
            self.logger.warning(
                "Using bin_slop = %g, bin_size = %g, b = %g\n"%(self.bin_slop,self.bin_size,self.b)+
                "It is recommended to use bin_slop <= %s in this case.\n"%max_good_slop+
                "Larger values of bin_slop (and hence b) may result in significant inaccuracies.")
        else:
            self.logger.debug("Using bin_slop = %g, b = %g",self.bin_slop,self.b)

        self._ro.brute = treecorr.config.get(self.config,'brute',bool,False)
        if self.brute:
            self.logger.info("Doing brute force calculation%s.",
                             self.brute is True and "" or
                             self.brute == 1 and " for first field" or
                             " for second field")
        self.coords = None
        self.metric = None
        self._ro.min_rpar = treecorr.config.get(self.config,'min_rpar',float,-sys.float_info.max)
        self._ro.max_rpar = treecorr.config.get(self.config,'max_rpar',float,sys.float_info.max)
        if self.min_rpar > self.max_rpar:
            raise ValueError("min_rpar must be <= max_rpar")
        period = treecorr.config.get(self.config,'period',float,0)
        self._ro.xperiod = treecorr.config.get(self.config,'xperiod',float,period)
        self._ro.yperiod = treecorr.config.get(self.config,'yperiod',float,period)
        self._ro.zperiod = treecorr.config.get(self.config,'zperiod',float,period)

        self._ro.var_method = treecorr.config.get(self.config,'var_method',str,'shot')
        self._ro.num_bootstrap = treecorr.config.get(self.config,'num_bootstrap',int,500)
        self.results = {}  # for jackknife, etc. store the results of each pair of patches.
        self.npatch1 = self.npatch2 = 1

    # Properties for all the read-only attributes ("ro" stands for "read-only")
    @property
    def output_dots(self): return self._ro.output_dots
    @property
    def bin_type(self): return self._ro.bin_type
    @property
    def sep_units(self): return self._ro.sep_units
    @property
    def _sep_units(self): return self._ro._sep_units
    @property
    def _log_sep_units(self): return self._ro._log_sep_units
    @property
    def min_sep(self): return self._ro.min_sep
    @property
    def max_sep(self): return self._ro.max_sep
    @property
    def bin_size(self): return self._ro.bin_size
    @property
    def nbins(self): return self._ro.nbins
    @property
    def logr(self): return self._ro.logr
    @property
    def rnom(self): return self._ro.rnom
    @property
    def left_edges(self): return self._ro.left_edges
    @property
    def right_edges(self): return self._ro.right_edges
    @property
    def top_edges(self): return self._ro.top_edges
    @property
    def bottom_edges(self): return self._ro.bottom_edges
    @property
    def _bintype(self): return self._ro._bintype
    @property
    def _nbins(self): return self._ro._nbins
    @property
    def _min_sep(self): return self._ro._min_sep
    @property
    def _max_sep(self): return self._ro._max_sep
    @property
    def _bin_size(self): return self._ro._bin_size
    @property
    def split_method(self): return self._ro.split_method
    @property
    def min_top(self): return self._ro.min_top
    @property
    def max_top(self): return self._ro.max_top
    @property
    def bin_slop(self): return self._ro.bin_slop
    @property
    def b(self): return self._ro.b
    @property
    def brute(self): return self._ro.brute
    @property
    def min_rpar(self): return self._ro.min_rpar
    @property
    def max_rpar(self): return self._ro.max_rpar
    @property
    def xperiod(self): return self._ro.xperiod
    @property
    def yperiod(self): return self._ro.yperiod
    @property
    def zperiod(self): return self._ro.zperiod
    @property
    def var_method(self): return self._ro.var_method
    @property
    def num_bootstrap(self): return self._ro.num_bootstrap
    @property
    def _d1(self): return self._ro._d1
    @property
    def _d2(self): return self._ro._d2

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_corr',None)
        d.pop('logger',None)  # Oh well.  This is just lost in the copy.  Can't be pickled.
        return d

    def __setstate__(self, d):
        self.__dict__ = d
        self._corr = None
        self.logger = treecorr.config.setup_logger(
                treecorr.config.get(self.config,'verbose',int,1),
                self.config.get('log_file',None))

    def _add_tot(self, i, j, c1, c2):
        # No op for all but NNCorrelation, which needs to add the tot value
        pass

    def _trivially_zero(self, c1, c2, metric):
        # For now, ignore the metric.  Just be conservative about how much space we need.
        x1,y1,z1,s1 = c1._get_center_size()
        x2,y2,z2,s2 = c2._get_center_size()
        d = ((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)**0.5
        return (d > s1 + s2 + 2*self._max_sep)  # The 2* is where we are being conservative.

    def _process_all_auto(self, cat1, metric, num_threads, comm, low_mem):

        def is_my_job(my_indices, i, j, n):
            # Helper function to figure out if a given (i,j) job should be done on the
            # current process.

            # Always my job if not using MPI.
            if my_indices is None:
                return True

            # Now the tricky part.  If using MPI, we need to divide up the jobs smartly.
            # The first point is to divvy up the auto jobs evenly.  This is where most of the
            # work is done, so we want those to be spreads as evenly as possibly across procs.
            # Therefore, if both indices are mine, then do the job.
            # This reduces the number of catalogs this machine needs to load up.
            # If the auto i,i and j,j are both my job, then i and j are already being loaded
            # on this machine, so also do that job.
            if i in my_indices and j in my_indices:
                self.logger.info("Rank %d: Job (%d,%d) is mine.",rank,i,j)
                return True

            # If neither index is mine, then it's not my job.
            if i not in my_indices and j not in my_indices:
                return False

            # For the other jobs, we want to minimize how many other catalogs need to be
            # loaded.  Unfortunately, the nature of pairs is such that we can't reduce this
            # too much.  For the set of jobs i,j where i belongs to proc 1 and j belongs to proc 2,
            # half of these pairs need to be assigned to each proc.
            # The best I could figure for this is to give even i to proc 1 and odd i to proc 2.
            # This means proc 1 has to load all the j catalogs, but proc 2 can skip half the i
            # catalogs.  This would naively have the result that procs with lower indices
            # have to load more catalogs than those with higher indices, since i < j.
            # So we reverse the procedure when j-i > n/2 to spread out the I/O more.
            if j-i < n//2:
                ret = i % 2 == (0 if i in my_indices else 1)
            else:
                ret = j % 2 == (0 if j in my_indices else 1)
            if ret:
                self.logger.info("Rank %d: Job (%d,%d) is mine.",rank,i,j)
            return ret

        if len(cat1) == 1:
            self.process_auto(cat1[0],metric,num_threads)
        else:
            # When patch processing, keep track of the pair-wise results.
            if self.npatch1 == 1:
                self.npatch1 = self.npatch2 = len(cat1)
            n = self.npatch1

            # Setup for deciding when this is my job.
            if comm:
                size = comm.Get_size()
                rank = comm.Get_rank()
                my_indices = np.arange(n * rank // size, n * (rank+1) // size)
                self.logger.info("Rank %d: My indices are %s",rank,my_indices)
            else:
                my_indices = None

            temp = self.copy()
            temp.results = {}  # Don't mess up the original results
            for ii,c1 in enumerate(cat1):
                i = c1.patch if c1.patch is not None else ii
                if is_my_job(my_indices, i, i, n):
                    temp.clear()
                    self.logger.info('Process patch %d auto',i)
                    temp.process_auto(c1,metric,num_threads)
                    self.results[(i,i)] = temp.copy()
                    self += temp
                for jj,c2 in list(enumerate(cat1))[::-1]:
                    j = c2.patch if c2.patch is not None else jj
                    if i < j and is_my_job(my_indices, i, j, n):
                        temp.clear()
                        if not self._trivially_zero(c1,c2,metric):
                            self.logger.info('Process patches %d,%d cross',i,j)
                            temp.process_cross(c1,c2,metric,num_threads)
                        else:
                            self.logger.info('Skipping %d,%d pair, which are too far apart ' +
                                             'for this set of separations',i,j)
                        if np.sum(temp.npairs) > 0:
                            self.results[(i,j)] = temp.copy()
                            self += temp
                        else:
                            # NNCorrelation needs to add the tot value
                            self._add_tot(i, j, c1, c2)
                        if low_mem and jj != ii+1:
                            # Don't unload i+1, since that's the next one we'll need.
                            c2.unload()
                if low_mem:
                    c1.unload()
            if comm is not None:
                rank = comm.Get_rank()
                size = comm.Get_size()
                self.logger.info("Rank %d: Completed jobs %s",rank,list(self.results.keys()))
                # Send all the results back to rank 0 process.
                if rank > 0:
                    comm.send(self, dest=0)
                else:
                    for p in range(1,size):
                        temp = comm.recv(source=p)
                        self += temp
                        self.results.update(temp.results)

    def _process_all_cross(self, cat1, cat2, metric, num_threads, comm, low_mem):

        def is_my_job(my_indices, i, j, n1, n2):
            # Helper function to figure out if a given (i,j) job should be done on the
            # current process.

            # Always my job if not using MPI.
            if my_indices is None:
                return True

            # This is much simpler than in the auto case, since the set of catalogs for
            # cat1 and cat2 are different, we can just split up one of them among the jobs.
            if n1 > n2:
                k = i
            else:
                k = j
            if k in my_indices:
                self.logger.info("Rank %d: Job (%d,%d) is mine.",rank,i,j)
                return True
            else:
                return False

        if treecorr.config.get(self.config,'pairwise',bool,False):
            import warnings
            warnings.warn("The pairwise option is slated to be removed in a future version. "+
                          "If you are actually using this parameter usefully, please "+
                          "open an issue to describe your use case.", FutureWarning)
            if len(cat1) != len(cat2):
                raise ValueError("Number of files for 1 and 2 must be equal for pairwise.")
            for c1,c2 in zip(cat1,cat2):
                if c1.ntot != c2.ntot:
                    raise ValueError("Number of objects must be equal for pairwise.")
                self.process_pairwise(c1,c2,metric,num_threads)
        elif len(cat1) == 1 and len(cat2) == 1:
            self.process_cross(cat1[0],cat2[0],metric,num_threads)
        else:
            # When patch processing, keep track of the pair-wise results.
            if self.npatch1 == 1:
                self.npatch1 = len(cat1)
            if self.npatch2 == 1:
                self.npatch2 = len(cat2)
            if self.npatch1 != self.npatch2 and self.npatch1 != 1 and self.npatch2 != 1:
                raise RuntimeError("Cross correlation requires both catalogs use the same patches.")

            # Setup for deciding when this is my job.
            n1 = self.npatch1
            n2 = self.npatch2
            if comm:
                size = comm.Get_size()
                rank = comm.Get_rank()
                if n1 > n2:
                    my_indices = np.arange(n1 * rank // size, n1 * (rank+1) // size)
                else:
                    my_indices = np.arange(n2 * rank // size, n2 * (rank+1) // size)
                self.logger.info("Rank %d: My indices are %s",rank,my_indices)
            else:
                my_indices = None

            temp = self.copy()
            temp.results = {}  # Don't mess up the original results
            for ii,c1 in enumerate(cat1):
                i = c1.patch if c1.patch is not None else ii
                for jj,c2 in enumerate(cat2):
                    j = c2.patch if c2.patch is not None else jj
                    if is_my_job(my_indices, i, j, n1, n2):
                        temp.clear()
                        if not self._trivially_zero(c1,c2,metric):
                            self.logger.info('Process patches %d,%d cross',i,j)
                            temp.process_cross(c1,c2,metric,num_threads)
                        else:
                            self.logger.info('Skipping %d,%d pair, which are too far apart ' +
                                             'for this set of separations',i,j)
                        if np.sum(temp.npairs) > 0:
                            self.results[(i,j)] = temp.copy()
                            self += temp
                        else:
                            # NNCorrelation needs to add the tot value
                            self._add_tot(i, j, c1, c2)
                        if low_mem:
                            c2.unload()
                if low_mem:
                    c1.unload()
            if comm is not None:
                rank = comm.Get_rank()
                size = comm.Get_size()
                self.logger.info("Rank %d: Completed jobs %s",rank,list(self.results.keys()))
                # Send all the results back to rank 0 process.
                if rank > 0:
                    comm.send(self, dest=0)
                else:
                    for p in range(1,size):
                        temp = comm.recv(source=p)
                        self += temp
                        self.results.update(temp.results)

    def getStat(self):
        """The standard statistic for the current correlation object as a 1-d array.

        Usually, this is just self.xi.  But if the metric is TwoD, this becomes self.xi.ravel().
        And for GGCorrelation, it is the concatenation of self.xip and self.xim.
        """
        return self.xi.ravel()

    def getWeight(self):
        """The weight array for the current correlation object as a 1-d array.

        This is the weight array corresponding to `getStat`. Usually just self.weight, but
        raveled for TwoD and duplicated for GGCorrelation to match what `getStat` does in
        those cases.
        """
        return self.weight.ravel()

    def estimate_cov(self, method):
        """Estimate the covariance matrix based on the data

        This function will calculate an estimate of the covariance matrix according to the
        given method.

        Options for ``method`` include:

            - 'shot' = The variance based on "shot noise" only.  This includes the Poisson
              counts of points for N statistics, shape noise for G statistics, and the observed
              scatter in the values for K statistics.  In this case, the returned covariance
              matrix will be diagonal, since there is no way to estimate the off-diagonal terms.
            - 'jackknife' = A jackknife estimate of the covariance matrix based on the scatter
              in the measurement when excluding one patch at a time.
            - 'sample' = An estimate based on the sample covariance of a set of samples,
              taken as the patches of the input catalog.
            - 'bootstrap' = A bootstrap covariance estimate. It selects patches at random with
              replacement and then generates the statistic using all the auto-correlations at
              their selected repetition plus all the cross terms that aren't actually auto terms.
            - 'marked_bootstrap' = An estimate based on a marked-point bootstrap resampling of the
              patches.  Similar to bootstrap, but only samples the patches of the first catalog and
              uses all patches from the second catalog that correspond to each patch selection of
              the first catalog.  cf. https://ui.adsabs.harvard.edu/abs/2008ApJ...681..726L/

        Both 'bootstrap' and 'marked_bootstrap' use the num_bootstrap parameter, which can be set on
        construction.

        .. note::

            For most classes, there is only a single statistic, so this calculates a covariance
            matrix for that vector.  `GGCorrelation` has two: ``xip`` and ``xim``, so in this
            case the full data vector is ``xip`` followed by ``xim``, and this calculates the
            covariance matrix for that full vector including both statistics.  The helper
            function `getStat` returns the relevant statistic in all cases.

        In all cases, the relevant processing needs to already have been completed and finalized.
        And for all methods other than 'shot', the processing should have involved an appropriate
        number of patches -- preferably more patches than the length of the vector for your
        statistic, although this is not checked.

        Parameters:
            method (str):   Which method to use to estimate the covariance matrix.

        Returns:
            A numpy array with the estimated covariance matrix.
        """
        return estimate_multi_cov([self], method)

    def _set_num_threads(self, num_threads):
        if num_threads is None:
            num_threads = self.config.get('num_threads',None)
        # Recheck.
        if num_threads is None:
            self.logger.debug('Set num_threads automatically')
        else:
            self.logger.debug('Set num_threads = %d',num_threads)
        treecorr.set_omp_threads(num_threads, self.logger)

    def _set_metric(self, metric, coords1, coords2=None):
        if metric is None:
            metric = treecorr.config.get(self.config,'metric',str,'Euclidean')
        if metric not in ['Rperp', 'OldRperp', 'FisherRperp', 'Rlens', 'Arc']:
            if self.min_rpar != -sys.float_info.max:
                raise ValueError("min_rpar is not valid for %s metric."%metric)
            if self.max_rpar != sys.float_info.max:
                raise ValueError("max_rpar is not valid for %s metric."%metric)
        coords, metric = treecorr.util.parse_metric(metric, coords1, coords2)
        if self.sep_units != '' and coords == '3d' and metric != 'Arc':
            raise ValueError("sep_units is invalid with 3d coordinates. "
                             "min_sep and max_sep should be in the same units as r (or x,y,z).")
        if self.coords is not None or self.metric is not None:
            if coords != self.coords:
                self.logger.warning("Detected a change in catalog coordinate systems.\n"+
                                    "This probably doesn't make sense!")
            if metric != self.metric:
                self.logger.warning("Detected a change in metric.\n"+
                                    "This probably doesn't make sense!")
        if metric == 'Periodic':
            if self.xperiod == 0 or self.yperiod == 0 or (coords=='3d' and self.zperiod == 0):
                raise ValueError("Periodic metric requires setting the period to use.")
        else:
            if self.xperiod != 0 or self.yperiod != 0 or self.zperiod != 0:
                raise ValueError("period options are not valid for %s metric."%metric)
        self.coords = coords  # These are the regular string values
        self.metric = metric
        self._coords = treecorr.util.coord_enum(coords)  # These are the C++-layer enums
        self._metric = treecorr.util.metric_enum(metric)

    def _apply_units(self, mask):
        if self.coords == 'spherical' and self.metric == 'Euclidean':
            # Then our distances are all angles.  Convert from the chord distance to a real angle.
            # L = 2 sin(theta/2)
            self.meanr[mask] = 2. * np.arcsin(self.meanr[mask]/2.)
            self.meanlogr[mask] = np.log( 2. * np.arcsin(np.exp(self.meanlogr[mask])/2.) )
        self.meanr[mask] /= self._sep_units
        self.meanlogr[mask] -= self._log_sep_units

    def _get_minmax_size(self):
        if self.metric == 'Euclidean':
            # The minimum size cell that will be useful is one where two cells that just barely
            # don't split have (d + s1 + s2) = minsep
            # The largest s2 we need to worry about is s2 = 2s1.
            # i.e. d = minsep - 3s1  and s1 = 0.5 * bd
            #      d = minsep - 1.5 bd
            #      d = minsep / (1+1.5 b)
            #      s = 0.5 * b * minsep / (1+1.5 b)
            #        = b * minsep / (2+3b)
            min_size = self._min_sep * self.b / (2.+3.*self.b)

            # The maximum size cell that will be useful is one where a cell of size s will
            # be split at the maximum separation even if the other size = 0.
            # i.e. max_size = max_sep * b
            max_size = self._max_sep * self.b
            return min_size, max_size
        else:
            # For other metrics, the above calculation doesn't really apply, so just skip
            # this relatively modest optimization and go all the way to the leaves.
            # (And for the max_size, always split 10 levels for the top-level cells.)
            return 0., 0.

    def sample_pairs(self, n, cat1, cat2, min_sep, max_sep, metric=None):
        """Return a random sample of n pairs whose separations fall between min_sep and max_sep.

        This would typically be used to get some random subset of the indices of pairs that
        fell into a particular bin of the correlation.  E.g. to get 100 pairs from the third
        bin of a `BinnedCorr2` instance, corr, you could write::

            >>> min_sep = corr.left_edges[2]   # third bin has i=2
            >>> max_sep = corr.right_edges[2]
            >>> i1, i2, sep = corr.sample_pairs(100, cat1, cat2, min_sep, max_sep)

        The min_sep and max_sep should use the same units as were defined when constructing
        the corr instance.

        The selection process will also use the same bin_slop as specified (either explicitly or
        implicitly) when constructing the corr instance.  This means that some of the pairs may
        have actual separations slightly outside of the specified range.  If you want a selection
        using an exact range without any slop, you should construct a new Correlation instance
        with bin_slop=0, and call sample_pairs with that.

        The returned separations will likewise correspond to the separation of the cells in the
        tree that TreeCorr used to place the pairs into the given bin.  Therefore, if these cells
        were not leaf cells, then they will not typically be equal to the real separations for the
        given metric.  If you care about the exact separations for each pair, you should either
        call sample_pairs from a Correlation instance with brute=True or recalculate the
        distances yourself from the original data.

        Also, note that min_sep and max_sep may be arbitrary.  There is no requirement that they
        be edges of one of the standard bins for this correlation function.  There is also no
        requirement that this correlation instance has already accumulated pairs via a call
        to process with these catalogs.

        Parameters:
            n (int):            How many samples to return.
            cat1 (Catalog):     The catalog from which to sample the first object of each pair.
            cat2 (Catalog):     The catalog from which to sample the second object of each pair.
                                (This may be the same as cat1.)
            min_sep (float):    The minimum separation for the returned pairs (modulo some slop
                                allowed by the bin_slop parameter).
            max_sep (float):    The maximum separation for the returned pairs (modulo some slop
                                allowed by the bin_slop parameter).
            metric (str):       Which metric to use.  See `Metrics` for details.  (default:
                                self.metric, or 'Euclidean' if not set yet)

        Returns:
            Tuple containing

                - i1 (array): indices of objects from cat1
                - i2 (array): indices of objects from cat2
                - sep (array): separations of the pairs of objects (i1,i2)
        """
        from .util import long_ptr as lp
        from .util import double_ptr as dp

        if metric is None:
            metric = self.config.get('metric', 'Euclidean')

        self._set_metric(metric, cat1.coords, cat2.coords)

        f1 = cat1.field
        f2 = cat2.field

        if f1 is None or f1._coords != self._coords:
            # I don't really know if it's possible to get the coords out of sync,
            # so the 2nd check might be superfluous.
            # The first one though is definitely possible, so we need to check that.
            self.logger.debug("In sample_pairs, making default field for cat1")
            min_size, max_size = self._get_minmax_size()
            f1 = cat1.getNField(min_size, max_size, self.split_method,
                                self.brute is True or self.brute == 1,
                                self.min_top, self.max_top, self.coords)
        if f2 is None or f2._coords != self._coords:
            self.logger.debug("In sample_pairs, making default field for cat2")
            min_size, max_size = self._get_minmax_size()
            f2 = cat2.getNField(min_size, max_size, self.split_method,
                                self.brute is True or self.brute == 2,
                                self.min_top, self.max_top, self.coords)

        # Apply units to min_sep, max_sep:
        min_sep *= self._sep_units
        max_sep *= self._sep_units

        i1 = np.zeros(n, dtype=int)
        i2 = np.zeros(n, dtype=int)
        sep = np.zeros(n, dtype=float)
        ntot = treecorr._lib.SamplePairs(self.corr, f1.data, f2.data, min_sep, max_sep,
                                         f1._d, f2._d, self._coords, self._bintype, self._metric,
                                         lp(i1), lp(i2), dp(sep), n)

        if ntot < n:
            n = ntot
            i1 = i1[:n]
            i2 = i2[:n]
            sep = sep[:n]
        # Convert back to nominal units
        sep /= self._sep_units
        self.logger.info("Sampled %d pairs out of a total of %d.", n, ntot)

        return i1, i2, sep

    def _calculate_xi_from_pairs(self, pairs):
        # Compute the xi data vector for the given list of pairs.
        # pairs is input as a list of (i,j) values.

        # This is the normal calculation.  It needs to be overridden when there are randoms.
        self.clear()
        self._sum([self.results[ij] for ij in pairs])
        self._finalize()

def _make_cov_design_matrix(corrs, plist, func):
    # vpairs is a list of pairs to use for each row of the design matrix.
    # Each row of vpairs is a list of (i,j) indices to use in that row.
    # We then compute the resulting data vector based on those pairs and save it as v[row]
    # We also make a parallel matrix of the weights in case the calling routing needs it.
    # So far, only sample uses the returned w, but it's very little overhead to compute it,
    # since _calculate_xi_from_pairs needs to calculate w anyway, so it's only a small
    # memory overhead to keep those around and return them.

    # Make a copy of the correlation objects, so we can overwrite things without breaking
    # the original.
    corrs = [c.copy() for c in corrs]

    # Figure out the full length of the data vector.
    vsize = len(func(corrs))

    # Swap order of plist.  Right now it's a list for each corr of a list for each row.
    # We want a list by row with a list for each corr.
    plist = list(zip(*plist))
    nrows = len(plist)

    # Make the empty return arrays.
    v = np.empty((nrows,vsize), dtype=float)
    w = np.zeros(nrows, dtype=float)

    for row, pairs in enumerate(plist):
        for c, cpairs in zip(corrs, pairs):
            c._calculate_xi_from_pairs(cpairs)
        v[row] = func(corrs)
        w[row] = np.sum([np.sum(c.getWeight()) for c in corrs])
    return v,w

def estimate_multi_cov(corrs, method, func=None):
    """Estimate the covariance matrix of multiple statistics.

    This is like the method `BinnedCorr2.estimate_cov`, except that it will acoommodate
    multiple statistics from a list ``corrs`` of `BinnedCorr2` objects.

    Options for ``method`` include:

        - 'shot' = The variance based on "shot noise" only.  This includes the Poisson
          counts of points for N statistics, shape noise for G statistics, and the observed
          scatter in the values for K statistics.  In this case, the returned covariance
          matrix will be diagonal, since there is no way to estimate the off-diagonal terms.
        - 'jackknife' = A jackknife estimate of the covariance matrix based on the scatter
          in the measurement when excluding one patch at a time.
        - 'sample' = An estimate based on the sample covariance of a set of samples,
          taken as the patches of the input catalog.
        - 'bootstrap' = A bootstrap covariance estimate. It selects patches at random with
          replacement and then generates the statistic using all the auto-correlations at
          their selected repetition plus all the cross terms that aren't actually auto terms.
        - 'marked_bootstrap' = An estimate based on a marked-point bootstrap resampling of the
          patches.  Similar to bootstrap, but only samples the patches of the first catalog and
          uses all patches from the second catalog that correspond to each patch selection of
          the first catalog.  cf. https://ui.adsabs.harvard.edu/abs/2008ApJ...681..726L/

    Both 'bootstrap' and 'marked_bootstrap' use the num_bootstrap parameter, which can be set on
    construction.

    For example, to find the combined covariance matrix for an NG tangential shear statistc,
    along with the GG xi+ and xi- from the same area, using jackknife covariance estimation,
    you would write::

        >>> cov = treecorr.estimate_multi_cov([ng,gg], 'jackknife')

    In all cases, the relevant processing needs to already have been completed and finalized.
    And for all methods other than 'shot', the processing should have involved an appropriate
    number of patches -- preferably more patches than the length of the vector for your
    statistic, although this is not checked.

    The default order of the covariance matrix is to simply concatenate the data vectors
    for each corr in the list ``corrs``.  However, if you want to so something more complicated,
    you may provide an arbitrary function, ``func``, which should act on the list of correlations.
    For instance, if you have several `GGCorrelation` objects and would like to order the
    covariance such that all xi+ results come first, and then all xi- results, you could do

        >>> func = lambda corrs: np.concatenate([c.xip for c in corrs] + [c.xim for c in corrs])

    Or if you want to compute the covariance matrix of some derived quantity like the ratio
    of two correlations, you could

        >>> func = lambda corrs: corrs[0].xi / corrs[1].xi

    The result of this func should be a single numpy array.

    .. note::

        The optional ``func`` parameter is not valid in conjunction with ``method='shot'``.
        It only works for the methods that are based on patch combinations.

    Parameters:
        corrs (list):       A list of `BinnedCorr2` instances.
        method (str):       Which method to use to estimate the covariance matrix.
        func (function):    A unary function that takes the list ``corrs`` and returns the
                            desired full data vector. [default: None, which is equivalent to
                            ``lambda corrs: np.concatenate([c.getStat() for c in corrs])``]

    Returns:
        A numpy array with the estimated covariance matrix.
    """
    if method == 'shot':
        if func is not None:
            raise ValueError("func is invalid with method='shot'")
        return _cov_shot(corrs)
    if func is None:
        func = lambda corrs: np.concatenate([c.getStat() for c in corrs])
    if method == 'jackknife':
        return _cov_jackknife(corrs, func)
    elif method == 'bootstrap':
        return _cov_bootstrap(corrs, func)
    elif method == 'marked_bootstrap':
        return _cov_marked(corrs, func)
    elif method == 'sample':
        return _cov_sample(corrs, func)
    else:
        raise ValueError("Invalid method: %s"%method)

def _cov_shot(corrs):
    # Shot noise "covariance" is just 1/RR or var(g)/weight or var(k)/weight, etc.
    # Except for NN, the denominator is always corr.weight.
    # For NN, the denominator is set by calculateXi to be RR.weight.
    # The numerators are set appropriately for each kind of correlation function as _var_num
    # when doing finalize, or for NN also in calculateXi.
    # We return it as a covariance matrix for consistency with the other cov functions,
    # but the off diagonal terms are all zero.
    vlist = []
    for c in corrs:
        v = c.getWeight().copy()
        mask1 = v != 0
        # Note: if w=0 anywhere, leave v=0 there, rather than divide by zero.
        v[mask1] = c._var_num / v[mask1]
        vlist.append(v)
    return np.diag(np.concatenate(vlist))  # Return as a covariance matrix

def _get_patch_nums(corrs, name):
    # Figure out what pairs (i,j) are possible for these correlation functions.
    # Returns npatch, all_pairs
    # all_pairs is a list of (i,j) values that any of the correlations have computed.

    pairs = list(corrs[0].results.keys())
    if len(pairs) == 0:
        raise ValueError("Using %s covariance requires using patches."%name)
    npatch = max(corrs[0].npatch1, corrs[0].npatch2)
    all_pairs = [pairs]  # Start these as lists for each corr instance.
    for c in corrs[1:]:
        pairs = list(c.results.keys())
        if len(pairs) == 0:
            raise ValueError("Using %s covariance requires using patches."%name)
        if (c.npatch1 != 1 and c.npatch1 != npatch) or (c.npatch2 != 1 and c.npatch2 != npatch):
            raise RuntimeError("All correlations must use the same number of patches")
        all_pairs.append(pairs)
    return npatch, all_pairs

def _cov_jackknife(corrs, func):
    # Calculate the jackknife covariance for the given statistics

    # The basic jackknife formula is:
    # C = (1-1/npatch) Sum_i (v_i - v_mean) (v_i - v_mean)^T
    # where v_i is the vector when excluding patch i, and v_mean is the mean of all {v_i}.
    #   v_i = Sum_jk!=i num_jk / Sum_jk!=i denom_jk

    npatch, all_pairs = _get_patch_nums(corrs, 'jackknife')

    plist = []
    for c, pairs in zip(corrs, all_pairs):
        if c.npatch2 == 1:
            vpairs = [ [(j,0) for j in range(c.npatch1) if j!=i] for i in range(c.npatch1) ]
        elif c.npatch1 == 1:
            vpairs = [ [(0,j) for j in range(c.npatch2) if j!=i] for i in range(c.npatch2) ]
        else:
            assert c.npatch1 == c.npatch2
            # For each i:
            #    Select all pairs where neither is i.
            vpairs = [ [(j,k) for j,k in pairs if j!=i and k!=i] for i in range(c.npatch1) ]
        plist.append(vpairs)

    v,w = _make_cov_design_matrix(corrs, plist, func)
    vmean = np.mean(v, axis=0)
    v -= vmean
    C = (1.-1./npatch) * v.T.dot(v)
    return C

def _cov_sample(corrs, func):
    # Calculate the sample covariance.

    # This is kind of the converse of the jackknife.  We take each patch and use any
    # correlations of it with any other patch.  The sample variance of these is the estimate
    # of the overall variance.

    # C = 1/(npatch-1) Sum_i w_i (v_i - v_mean) (v_i - v_mean)^T
    # where v_i = Sum_j num_ij / Sum_j denom_ij
    # and w_i is the fraction of the total weight in each patch

    npatch, all_pairs = _get_patch_nums(corrs, 'sample')

    plist = []
    for c, pairs in zip(corrs, all_pairs):
        if c.npatch2 == 1:
            vpairs = [ [(i,0)] for i in range(c.npatch1) ]
        elif c.npatch1 == 1:
            vpairs = [ [(0,i)] for i in range(c.npatch2) ]
        else:
            assert c.npatch1 == c.npatch2
            # Note: It's not obvious to me a priori which of these should be the right choice.
            #       Empirically, they both underestimate the variance, but the second one
            #       does so less on the tests I have in test_patch.py.  So that's the one I'm
            #       using.
            # For each i:
            #    Select all pairs where either is i.
            #vpairs = [ [(j,k) for j,k in pairs if j==i or k==i] for i in range(c.npatch1) ]
            # For each i:
            #    Select all pairs where first is i.
            vpairs = [ [(j,k) for j,k in pairs if j==i] for i in range(c.npatch1) ]
        if any([len(v) == 0 for v in vpairs]):
            raise RuntimeError("Cannot compute sample variance when some patches have no data.")
        plist.append(vpairs)

    v,w = _make_cov_design_matrix(corrs, plist, func)
    w /= np.sum(w)  # Now w is the fractional weight for each patch

    vmean = np.mean(v, axis=0)
    v -= vmean
    C = 1./(npatch-1) * (w * v.T).dot(v)
    return C

def _cov_marked(corrs, func):
    # Calculate the marked-point bootstrap covariance

    # This is based on the article A Valid and Fast Spatial Bootstrap for Correlation Functions
    # by Ji Meng Loh, 2008, cf. https://ui.adsabs.harvard.edu/abs/2008ApJ...681..726L/abstract

    # We do a bootstrap sampling of the patches.  For each patch selected, we include
    # all pairs that have the sampled patch in the first position.  In the Loh prescription,
    # the sums of pairs with a given choice of first patch would be the marks.  Here, we
    # don't quite do that, since the marks would involve a ratio, so the division is biased
    # when somewhat noisy.  Rather, we sum the numerators and denominators of the marks
    # separately and divide the sums.

    # From the bootstrap totals, v_i, the estimated covariance matrix is

    # C = 1/(nboot) Sum_i (v_i - v_mean) (v_i - v_mean)^T

    npatch, all_pairs = _get_patch_nums(corrs, 'marked_bootstrap')

    nboot = np.max([c.num_bootstrap for c in corrs])  # use the maximum if they differ.
    plist = []
    for c, pairs in zip(corrs, all_pairs):
        vpairs = []
        if c.npatch1 != 1 and c.npatch2 != 1:
            # Precompute this for use below.  (Makes the list comprehension much faster.)
            ok = np.zeros((c.npatch1, c.npatch1), dtype=bool)
            for (i,j) in pairs:
                ok[i,j] = True
        for k in range(nboot):
            # Select a random set of indices to use.  (Will have repeats.)
            indx = np.random.randint(npatch, size=npatch)
            if c.npatch2 == 1:
                vpairs1 = [ (i,0) for i in indx ]
            elif c.npatch1 == 1:
                vpairs1 = [ (0,i) for i in indx ]
            else:
                assert c.npatch1 == c.npatch2
                # Select all pairs where first point is in indx (repeating i as appropriate)
                vpairs1 = [ (i,j) for i in indx for j in range(c.npatch2) if ok[i,j] ]
            vpairs.append(vpairs1)
        plist.append(vpairs)

    v,w = _make_cov_design_matrix(corrs, plist, func)
    vmean = np.mean(v, axis=0)
    v -= vmean
    C = 1./(nboot-1) * v.T.dot(v)
    return C

def _cov_bootstrap(corrs, func):
    # Calculate the 2-patch bootstrap covariance estimate.

    # This is a different version of the bootstrap idea.  It selects patches at random with
    # replacement, and then generates the statistic using all the auto-correlations at their
    # selected repetition plus all the cross terms, which aren't actually auto terms.
    # It seems to do a slightly better job than the marked-point bootstrap above from the
    # tests done in the test suite.  But the difference is generally pretty small.

    npatch, all_pairs = _get_patch_nums(corrs, 'bootstrap')

    nboot = np.max([c.num_bootstrap for c in corrs])  # use the maximum if they differ.
    plist = []
    for c, pairs in zip(corrs, all_pairs):
        vpairs = []
        if c.npatch1 != 1 and c.npatch2 != 1:
            # Precompute this for use below.  (Makes the list comprehension much faster.)
            ok = np.zeros((c.npatch1, c.npatch1), dtype=bool)
            for (i,j) in pairs:
                if i != j:
                    ok[i,j] = True
        for k in range(nboot):
            indx = np.random.randint(npatch, size=npatch)
            if c.npatch2 == 1:
                vpairs1 = [ (i,0) for i in indx ]
            elif c.npatch1 == 1:
                vpairs1 = [ (0,i) for i in indx ]
            else:
                assert c.npatch1 == c.npatch2
                # Include all represented auto-correlations once, repeating as appropriate
                vpairs1 = [ (i,i) for i in indx if (i,i) in pairs ]

                # And all other pairs that aren't really auto-correlations
                # This is way faster with the precomputed ok matrix.
                # Like 0.005 seconds per call rather than 1.2 seconds for 128 patches!
                temp = [ (i,j) for i in indx for j in indx if ok[i,j] ]
                vpairs1.extend(temp)
            vpairs.append(vpairs1)
        plist.append(vpairs)

    v,w = _make_cov_design_matrix(corrs, plist, func)
    vmean = np.mean(v, axis=0)
    v -= vmean
    C = 1./(nboot-1) * v.T.dot(v)
    return C
