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

import numpy as np
import treecorr
import os
import coord
import math
import time

from test_helper import get_script_name, do_pickle, assert_raises, CaptureLog, timer, assert_warns
from test_helper import is_ccw, is_ccw_3d

@timer
def test_logruv_binning():
    # Test some basic properties of the base class
    def check_arrays(nnn):
        np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
        np.testing.assert_almost_equal(nnn.ubin_size * nnn.nubins, nnn.max_u-nnn.min_u)
        np.testing.assert_almost_equal(nnn.vbin_size * nnn.nvbins, nnn.max_v-nnn.min_v)
        np.testing.assert_equal(nnn.logr1d.shape, (nnn.nbins,) )
        np.testing.assert_almost_equal(nnn.logr1d[0], math.log(nnn.min_sep) + 0.5*nnn.bin_size)
        np.testing.assert_almost_equal(nnn.logr1d[-1], math.log(nnn.max_sep) - 0.5*nnn.bin_size)
        np.testing.assert_equal(nnn.logr.shape, (nnn.nbins, nnn.nubins, 2*nnn.nvbins) )
        np.testing.assert_almost_equal(nnn.logr[:,0,0], nnn.logr1d)
        np.testing.assert_almost_equal(nnn.logr[:,-1,-1], nnn.logr1d)
        assert len(nnn.logr) == nnn.nbins
        np.testing.assert_equal(nnn.u1d.shape, (nnn.nubins,) )
        np.testing.assert_almost_equal(nnn.u1d[0], nnn.min_u + 0.5*nnn.ubin_size)
        np.testing.assert_almost_equal(nnn.u1d[-1], nnn.max_u - 0.5*nnn.ubin_size)
        np.testing.assert_equal(nnn.u.shape, (nnn.nbins, nnn.nubins, 2*nnn.nvbins) )
        np.testing.assert_almost_equal(nnn.u[0,:,0], nnn.u1d)
        np.testing.assert_almost_equal(nnn.u[-1,:,-1], nnn.u1d)
        np.testing.assert_equal(nnn.v1d.shape, (2*nnn.nvbins,) )
        np.testing.assert_almost_equal(nnn.v1d[0], -nnn.max_v + 0.5*nnn.vbin_size)
        np.testing.assert_almost_equal(nnn.v1d[-1], nnn.max_v - 0.5*nnn.vbin_size)
        np.testing.assert_almost_equal(nnn.v1d[nnn.nvbins], nnn.min_v + 0.5*nnn.vbin_size)
        np.testing.assert_almost_equal(nnn.v1d[nnn.nvbins-1], -nnn.min_v - 0.5*nnn.vbin_size)
        np.testing.assert_equal(nnn.v.shape, (nnn.nbins, nnn.nubins, 2*nnn.nvbins) )
        np.testing.assert_almost_equal(nnn.v[0,0,:], nnn.v1d)
        np.testing.assert_almost_equal(nnn.v[-1,-1,:], nnn.v1d)

    def check_defaultuv(nnn):
        assert nnn.min_u == 0.
        assert nnn.max_u == 1.
        assert nnn.nubins == np.ceil(1./nnn.ubin_size)
        assert nnn.min_v == 0.
        assert nnn.max_v == 1.
        assert nnn.nvbins == np.ceil(1./nnn.vbin_size)

    # Check the different ways to set up the binning:
    # Omit bin_size
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, bin_type='LogRUV')
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_defaultuv(nnn)
    check_arrays(nnn)

    # Specify min, max, n for u,v too.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20,
                                  min_u=0.2, max_u=0.9, nubins=12,
                                  min_v=0., max_v=0.2, nvbins=2)
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    assert nnn.min_u == 0.2
    assert nnn.max_u == 0.9
    assert nnn.nubins == 12
    assert nnn.min_v == 0.
    assert nnn.max_v == 0.2
    assert nnn.nvbins == 2
    check_arrays(nnn)

    # Omit min_sep
    nnn = treecorr.NNNCorrelation(max_sep=20, nbins=20, bin_size=0.1)
    assert nnn.bin_size == 0.1
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_defaultuv(nnn)
    check_arrays(nnn)

    # Specify max, n, bs for u,v too.
    nnn = treecorr.NNNCorrelation(max_sep=20, nbins=20, bin_size=0.1,
                                  max_u=0.9, nubins=3, ubin_size=0.05,
                                  max_v=0.4, nvbins=4, vbin_size=0.05)
    assert nnn.bin_size == 0.1
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    assert np.isclose(nnn.ubin_size, 0.05)
    assert np.isclose(nnn.min_u, 0.75)
    assert nnn.max_u == 0.9
    assert nnn.nubins == 3
    assert np.isclose(nnn.vbin_size, 0.05)
    assert np.isclose(nnn.min_v, 0.2)
    assert nnn.max_v == 0.4
    assert nnn.nvbins == 4
    check_arrays(nnn)

    # Omit max_sep
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=20, bin_size=0.1)
    assert nnn.bin_size == 0.1
    assert nnn.min_sep == 5.
    assert nnn.nbins == 20
    check_defaultuv(nnn)
    check_arrays(nnn)
    # Specify min, n, bs for u,v too.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=20, bin_size=0.1,
                                  min_u=0.7, nubins=4, ubin_size=0.05,
                                  min_v=0.2, nvbins=4, vbin_size=0.05)
    assert nnn.min_sep == 5.
    assert nnn.bin_size == 0.1
    assert nnn.nbins == 20
    assert nnn.min_u == 0.7
    assert np.isclose(nnn.ubin_size, 0.05)
    assert nnn.nubins == 4
    assert nnn.min_v == 0.2
    assert nnn.max_v == 0.4
    assert np.isclose(nnn.vbin_size, 0.05)
    assert nnn.nvbins == 4
    check_arrays(nnn)

    # Omit nbins
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1)
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    check_defaultuv(nnn)
    check_arrays(nnn)
    # Specify min, max, bs for u,v too.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  min_u=0.2, max_u=0.9, ubin_size=0.03,
                                  min_v=0.1, max_v=0.3, vbin_size=0.07)
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.bin_size <= 0.1
    assert nnn.min_u == 0.2
    assert nnn.max_u == 0.9
    assert nnn.nubins == 24
    assert np.isclose(nnn.ubin_size, 0.7/24)
    assert nnn.min_v == 0.1
    assert nnn.max_v == 0.3
    assert nnn.nvbins == 3
    assert np.isclose(nnn.vbin_size, 0.2/3)
    check_arrays(nnn)

    # If only one of min/max v are set, respect that
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  min_u=0.2, ubin_size=0.03,
                                  min_v=0.2, vbin_size=0.07)
    assert nnn.min_u == 0.2
    assert nnn.max_u == 1.
    assert nnn.nubins == 27
    assert np.isclose(nnn.ubin_size, 0.8/27)
    assert nnn.min_v == 0.2
    assert nnn.max_v == 1.
    assert nnn.nvbins == 12
    assert np.isclose(nnn.vbin_size, 0.8/12)
    check_arrays(nnn)
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  max_u=0.2, ubin_size=0.03,
                                  max_v=0.2, vbin_size=0.07)
    assert nnn.min_u == 0.
    assert nnn.max_u == 0.2
    assert nnn.nubins == 7
    assert np.isclose(nnn.ubin_size, 0.2/7)
    assert nnn.min_v == 0.
    assert nnn.max_v == 0.2
    assert nnn.nvbins == 3
    assert np.isclose(nnn.vbin_size, 0.2/3)
    check_arrays(nnn)

    # If only vbin_size is set for v, automatically figure out others.
    # (And if necessary adjust the bin_size down a bit.)
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  ubin_size=0.3, vbin_size=0.3)
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.min_u == 0.
    assert nnn.max_u == 1.
    assert nnn.nubins == 4
    assert np.isclose(nnn.ubin_size, 0.25)
    assert nnn.min_v == 0.
    assert nnn.max_v == 1.
    assert nnn.nvbins == 4
    assert np.isclose(nnn.vbin_size, 0.25)
    check_arrays(nnn)

    # If only nvbins is set for v, automatically figure out others.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  nubins=5, nvbins=5)
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.min_u == 0.
    assert nnn.max_u == 1.
    assert nnn.nubins == 5
    assert np.isclose(nnn.ubin_size,0.2)
    assert nnn.min_v == 0.
    assert nnn.max_v == 1.
    assert nnn.nvbins == 5
    assert np.isclose(nnn.vbin_size,0.2)
    check_arrays(nnn)

    # If both nvbins and vbin_size are set, set min/max automatically
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  ubin_size=0.1, nubins=5,
                                  vbin_size=0.1, nvbins=5)
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.ubin_size == 0.1
    assert nnn.nubins == 5
    assert nnn.max_u == 1.
    assert np.isclose(nnn.min_u,0.5)
    assert nnn.vbin_size == 0.1
    assert nnn.nvbins == 5
    assert nnn.min_v == 0.
    assert np.isclose(nnn.max_v,0.5)
    check_arrays(nnn)

    assert_raises(TypeError, treecorr.NNNCorrelation)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5)
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, bin_size=0.1)
    assert_raises(TypeError, treecorr.NNNCorrelation, nbins=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, bin_size=0.1)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, nbins=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20, bin_size=0.1)
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20, nbins=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, bin_size=0.1, nbins=20)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1, nbins=20)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, bin_size=0.1)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  bin_type='Log')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  bin_type='Linear')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  bin_type='TwoD')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  bin_type='Invalid')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_u=0.3, max_u=0.9, ubin_size=0.1, nubins=6)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_u=0.9, max_u=0.3)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_u=-0.1, max_u=0.3)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_u=0.1, max_u=1.3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_v=0.1, max_v=0.9, vbin_size=0.1, nvbins=9)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_v=0.9, max_v=0.3)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_v=-0.1, max_v=0.3)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_v=0.1, max_v=1.3)
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  split_method='invalid')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  phi_bin_size=0.3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  nphi_bins=3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_phi=0.3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  max_phi=0.3)

    # Check the use of sep_units
    # radians
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='radians')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5.)
    np.testing.assert_almost_equal(nnn._max_sep, 20.)
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_defaultuv(nnn)
    check_arrays(nnn)

    # arcsec
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='arcsec')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180/3600)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180/3600)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    # Note that logr is in the separation units, not radians.
    np.testing.assert_almost_equal(nnn.logr[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logr[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logr) == nnn.nbins
    check_defaultuv(nnn)

    # arcmin
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='arcmin')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180/60)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180/60)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logr[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logr[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logr) == nnn.nbins
    check_defaultuv(nnn)

    # degrees
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='degrees')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logr[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logr[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logr) == nnn.nbins
    check_defaultuv(nnn)

    # hours
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='hours')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/12)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/12)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logr[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logr[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logr) == nnn.nbins
    check_defaultuv(nnn)

    # Check bin_slop
    # Start with default behavior
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07)
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)
    np.testing.assert_almost_equal(nnn.bv, 0.07)

    # Explicitly set bin_slop=1.0 does the same thing.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=1.0,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07)
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)
    np.testing.assert_almost_equal(nnn.bv, 0.07)

    # Use a smaller bin_slop
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=0.2,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07)
    assert nnn.bin_slop == 0.2
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.02)
    np.testing.assert_almost_equal(nnn.bu, 0.006)
    np.testing.assert_almost_equal(nnn.bv, 0.014)

    # Use bin_slop == 0
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=0.0,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07)
    assert nnn.bin_slop == 0.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.0)
    np.testing.assert_almost_equal(nnn.bu, 0.0)
    np.testing.assert_almost_equal(nnn.bv, 0.0)

    # Bigger bin_slop
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=2.0,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07, verbose=0)
    assert nnn.bin_slop == 2.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.2)
    np.testing.assert_almost_equal(nnn.bu, 0.06)
    np.testing.assert_almost_equal(nnn.bv, 0.14)

    # With bin_size > 0.1, explicit bin_slop=1.0 is accepted.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.4, bin_slop=1.0,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07, verbose=0)
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.4
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.4)
    np.testing.assert_almost_equal(nnn.bu, 0.03)
    np.testing.assert_almost_equal(nnn.bv, 0.07)

    # But implicit bin_slop is reduced so that b = 0.1
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.4,
                                  min_u=0., max_u=0.9, ubin_size=0.03,
                                  min_v=0., max_v=0.21, vbin_size=0.07)
    assert nnn.bin_size == 0.4
    assert np.isclose(nnn.ubin_size, 0.03)
    assert np.isclose(nnn.vbin_size, 0.07)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)
    np.testing.assert_almost_equal(nnn.bv, 0.07)
    np.testing.assert_almost_equal(nnn.bin_slop, 0.25)

    # Separately for each of the three parameters
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.05,
                                  min_u=0., max_u=0.9, ubin_size=0.3,
                                  min_v=0., max_v=0.17, vbin_size=0.17)
    assert nnn.bin_size == 0.05
    assert np.isclose(nnn.ubin_size, 0.3)
    assert np.isclose(nnn.vbin_size, 0.17)
    np.testing.assert_almost_equal(nnn.b, 0.05)
    np.testing.assert_almost_equal(nnn.bu, 0.1)
    np.testing.assert_almost_equal(nnn.bv, 0.1)
    np.testing.assert_almost_equal(nnn.bin_slop, 1.0) # The stored bin_slop is just for lnr

@timer
def test_logsas_binning():
    # Test some basic properties of the base class
    def check_arrays(nnn):
        np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
        np.testing.assert_almost_equal(nnn.phi_bin_size * nnn.nphi_bins, nnn.max_phi-nnn.min_phi)
        np.testing.assert_equal(nnn.logr1d.shape, (nnn.nbins,) )
        np.testing.assert_almost_equal(nnn.logr1d[0], math.log(nnn.min_sep) + 0.5*nnn.bin_size)
        np.testing.assert_almost_equal(nnn.logr1d[-1], math.log(nnn.max_sep) - 0.5*nnn.bin_size)
        np.testing.assert_equal(nnn.logd2.shape, (nnn.nbins, nnn.nphi_bins, nnn.nbins))
        np.testing.assert_almost_equal(nnn.logd2[:,0,0], nnn.logr1d)
        np.testing.assert_almost_equal(nnn.logd2[:,-1,-1], nnn.logr1d)
        np.testing.assert_equal(nnn.logd3.shape, (nnn.nbins, nnn.nphi_bins, nnn.nbins))
        np.testing.assert_almost_equal(nnn.logd3[0,0,:], nnn.logr1d)
        np.testing.assert_almost_equal(nnn.logd3[-1,-1,:], nnn.logr1d)
        assert len(nnn.logd2) == nnn.nbins
        assert len(nnn.logd3) == nnn.nbins
        np.testing.assert_equal(nnn.phi1d.shape, (nnn.nphi_bins,) )
        np.testing.assert_almost_equal(nnn.phi1d[0], nnn.min_phi + 0.5*nnn.phi_bin_size)
        np.testing.assert_almost_equal(nnn.phi1d[-1], nnn.max_phi - 0.5*nnn.phi_bin_size)
        np.testing.assert_equal(nnn.phi.shape, (nnn.nbins, nnn.nphi_bins, nnn.nbins))
        np.testing.assert_almost_equal(nnn.phi[0,:,0], nnn.phi1d)
        np.testing.assert_almost_equal(nnn.phi[-1,:,-1], nnn.phi1d)

    def check_default_phi(nnn):
        assert nnn.min_phi == 0.
        assert nnn.max_phi == np.pi
        assert nnn.nphi_bins == np.ceil(np.pi/nnn.phi_bin_size)

    # Check the different ways to set up the binning:
    # Omit bin_size
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, bin_type='LogSAS')
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_default_phi(nnn)
    check_arrays(nnn)

    # Specify min, max, n for phi too.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20,
                                  min_phi=0.2, max_phi=0.9, nphi_bins=12,
                                  bin_type='LogSAS')
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    assert nnn.min_phi == 0.2
    assert nnn.max_phi == 0.9
    assert nnn.nphi_bins == 12
    check_arrays(nnn)

    # Omit min_sep
    nnn = treecorr.NNNCorrelation(max_sep=20, nbins=20, bin_size=0.1, bin_type='LogSAS')
    assert nnn.bin_size == 0.1
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_default_phi(nnn)
    check_arrays(nnn)

    # Specify max, n, bs for phi too.
    nnn = treecorr.NNNCorrelation(max_sep=20, nbins=20, bin_size=0.1,
                                  max_phi=0.9, nphi_bins=3, phi_bin_size=0.05,
                                  bin_type='LogSAS')
    assert nnn.bin_size == 0.1
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    assert np.isclose(nnn.phi_bin_size, 0.05)
    assert np.isclose(nnn.min_phi, 0.75)
    assert nnn.max_phi == 0.9
    assert nnn.nphi_bins == 3
    check_arrays(nnn)

    # Omit max_sep
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=20, bin_size=0.1, bin_type='LogSAS')
    assert nnn.bin_size == 0.1
    assert nnn.min_sep == 5.
    assert nnn.nbins == 20
    check_default_phi(nnn)
    check_arrays(nnn)
    # Specify min, n, bs for phi too.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=20, bin_size=0.1,
                                  min_phi=0.7, nphi_bins=4, phi_bin_size=0.05,
                                  bin_type='LogSAS')
    assert nnn.min_sep == 5.
    assert nnn.bin_size == 0.1
    assert nnn.nbins == 20
    assert nnn.min_phi == 0.7
    assert np.isclose(nnn.phi_bin_size, 0.05)
    assert nnn.nphi_bins == 4
    check_arrays(nnn)

    # Omit nbins
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1, bin_type='LogSAS')
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    check_default_phi(nnn)
    check_arrays(nnn)
    # Specify min, max, bs for phi too.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  min_phi=0.2, max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.bin_size <= 0.1
    assert nnn.min_phi == 0.2
    assert nnn.max_phi == 0.9
    assert nnn.nphi_bins == 24
    assert np.isclose(nnn.phi_bin_size, 0.7/24)
    check_arrays(nnn)

    # If only one of min/max phi are set, respect that
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  min_phi=0.2, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.min_phi == 0.2
    assert nnn.max_phi == np.pi
    assert nnn.nphi_bins == 99
    assert np.isclose(nnn.phi_bin_size, (np.pi-0.2)/99)
    check_arrays(nnn)
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  max_phi=0.2, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.min_phi == 0.
    assert nnn.max_phi == 0.2
    assert nnn.nphi_bins == 7
    assert np.isclose(nnn.phi_bin_size, 0.2/7)
    check_arrays(nnn)

    # If only phi_bin_size is set for phi, automatically figure out others.
    # (And if necessary adjust the bin_size down a bit.)
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  phi_bin_size=0.3, bin_type='LogSAS')
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.min_phi == 0.
    assert nnn.max_phi == np.pi
    assert nnn.nphi_bins == 11
    assert np.isclose(nnn.phi_bin_size, np.pi/11)
    check_arrays(nnn)

    # If only nphi_bins is set for phi, automatically figure out others.
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  nphi_bins=5, bin_type='LogSAS')
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.min_phi == 0.
    assert nnn.max_phi == np.pi
    assert nnn.nphi_bins == 5
    assert np.isclose(nnn.phi_bin_size, np.pi/5)
    check_arrays(nnn)

    # If both nphi_bins and phi_bin_size are set, set min/max automatically
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, bin_size=0.1,
                                  phi_bin_size=0.1, nphi_bins=5,
                                  bin_type='LogSAS')
    assert nnn.bin_size <= 0.1
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.phi_bin_size == 0.1
    assert nnn.nphi_bins == 5
    assert nnn.min_phi == 0.
    assert np.isclose(nnn.max_phi,0.5)
    check_arrays(nnn)

    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, bin_size=0.1, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, nbins=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, bin_size=0.1, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, nbins=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20, bin_size=0.1, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, max_sep=20, nbins=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, bin_size=0.1, nbins=20, bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  nbins=20, bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, bin_size=0.1,
                  bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_phi=0.3, max_phi=0.9, phi_bin_size=0.1, nphi_bins=6, bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_phi=0.9, max_phi=0.3, bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_phi=-0.1, max_phi=0.3, bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  min_phi=0.1, max_phi=7.3, bin_type='LogSAS')
    assert_raises(ValueError, treecorr.NNNCorrelation, min_sep=20, max_sep=5, nbins=20,
                  split_method='invalid', bin_type='LogSAS')
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', nubins=3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', ubin_size=0.2)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', min_u=0.2)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', max_u=0.2)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', nvbins=3)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', vbin_size=0.2)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', min_v=0.2)
    assert_raises(TypeError, treecorr.NNNCorrelation, min_sep=5, max_sep=20, bin_size=0.1,
                  bin_type='LogSAS', max_v=0.2)

    # Check the use of sep_units
    # radians
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='radians',
                                  bin_type='LogSAS')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5.)
    np.testing.assert_almost_equal(nnn._max_sep, 20.)
    assert nnn.min_sep == 5.
    assert nnn.max_sep == 20.
    assert nnn.nbins == 20
    check_default_phi(nnn)
    check_arrays(nnn)

    # arcsec
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='arcsec',
                                  bin_type='LogSAS')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180/3600)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180/3600)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    # Note that logd2 is in the separation units, not radians.
    np.testing.assert_almost_equal(nnn.logd2[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd2[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd2) == nnn.nbins
    np.testing.assert_almost_equal(nnn.logd3[:,:,0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd3[:,:,-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd3) == nnn.nbins
    check_default_phi(nnn)

    # arcmin
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='arcmin',
                                  bin_type='LogSAS')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180/60)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180/60)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logd2[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd2[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd2) == nnn.nbins
    np.testing.assert_almost_equal(nnn.logd3[:,:,0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd3[:,:,-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd3) == nnn.nbins
    check_default_phi(nnn)

    # degrees
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='degrees',
                                  bin_type='LogSAS')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/180)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/180)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logd2[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd2[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd2) == nnn.nbins
    np.testing.assert_almost_equal(nnn.logd3[:,:,0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd3[:,:,-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd3) == nnn.nbins
    check_default_phi(nnn)

    # hours
    nnn = treecorr.NNNCorrelation(min_sep=5, max_sep=20, nbins=20, sep_units='hours',
                                  bin_type='LogSAS')
    np.testing.assert_almost_equal(nnn.min_sep, 5.)
    np.testing.assert_almost_equal(nnn.max_sep, 20.)
    np.testing.assert_almost_equal(nnn._min_sep, 5. * math.pi/12)
    np.testing.assert_almost_equal(nnn._max_sep, 20. * math.pi/12)
    assert nnn.nbins == 20
    np.testing.assert_almost_equal(nnn.bin_size * nnn.nbins, math.log(nnn.max_sep/nnn.min_sep))
    np.testing.assert_almost_equal(nnn.logd2[0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd2[-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd2) == nnn.nbins
    np.testing.assert_almost_equal(nnn.logd3[:,:,0], math.log(5) + 0.5*nnn.bin_size)
    np.testing.assert_almost_equal(nnn.logd3[:,:,-1], math.log(20) - 0.5*nnn.bin_size)
    assert len(nnn.logd3) == nnn.nbins
    check_default_phi(nnn)

    # Check bin_slop
    # Start with default behavior
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)

    # Explicitly set bin_slop=1.0 does the same thing.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=1.0,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)

    # Use a smaller bin_slop
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=0.2,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 0.2
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.02)
    np.testing.assert_almost_equal(nnn.bu, 0.006)

    # Use bin_slop == 0
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=0.0,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 0.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.0)
    np.testing.assert_almost_equal(nnn.bu, 0.0)

    # Bigger bin_slop
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.1, bin_slop=2.0,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 2.0
    assert nnn.bin_size == 0.1
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.2)
    np.testing.assert_almost_equal(nnn.bu, 0.06)

    # With bin_size > 0.1, explicit bin_slop=1.0 is accepted.
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.4, bin_slop=1.0,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_slop == 1.0
    assert nnn.bin_size == 0.4
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.4)
    np.testing.assert_almost_equal(nnn.bu, 0.03)

    # But implicit bin_slop is reduced so that b = 0.1
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.4,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.03,
                                  bin_type='LogSAS')
    assert nnn.bin_size == 0.4
    assert np.isclose(nnn.phi_bin_size, 0.03)
    np.testing.assert_almost_equal(nnn.b, 0.1)
    np.testing.assert_almost_equal(nnn.bu, 0.03)
    np.testing.assert_almost_equal(nnn.bin_slop, 0.25)

    # Separately for each of the three parameters
    nnn = treecorr.NNNCorrelation(min_sep=5, nbins=14, bin_size=0.05,
                                  min_phi=0., max_phi=0.9, phi_bin_size=0.3,
                                  bin_type='LogSAS')
    assert nnn.bin_size == 0.05
    assert np.isclose(nnn.phi_bin_size, 0.3)
    np.testing.assert_almost_equal(nnn.b, 0.05)
    np.testing.assert_almost_equal(nnn.bu, 0.1)
    np.testing.assert_almost_equal(nnn.bin_slop, 1.0) # The stored bin_slop is just for lnr

@timer
def test_direct_logruv_auto():
    # If the catalogs are small enough, we can do a direct count of the number of triangles
    # to see if comes out right.  This should exactly match the treecorr code if bin_slop=0.

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    cat = treecorr.Catalog(x=x, y=y)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=1)
    ddd.process(cat)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(ngal):
        for j in range(i+1,ngal):
            for k in range(j+1,ngal):
                dij = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2)
                dik = np.sqrt((x[i]-x[k])**2 + (y[i]-y[k])**2)
                djk = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw(x[i],y[i],x[j],y[j],x[k],y[k])
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x[j],y[j],x[i],y[i],x[k],y[k])
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x[j],y[j],x[k],y[k],x[i],y[i])
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x[i],y[i],x[k],y[k],x[j],y[j])
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x[k],y[k],x[i],y[i],x[j],y[j])
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x[k],y[k],x[j],y[j],x[i],y[i])

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Check that running via the corr3 script works correctly.
    file_name = os.path.join('data','nnn_direct_data.dat')
    with open(file_name, 'w') as fid:
        for i in range(ngal):
            fid.write(('%.20f %.20f\n')%(x[i],y[i]))
    L = 10*s
    nrand = ngal
    rx = (rng.random_sample(nrand)-0.5) * L
    ry = (rng.random_sample(nrand)-0.5) * L
    rcat = treecorr.Catalog(x=rx, y=ry)
    rand_file_name = os.path.join('data','nnn_direct_rand.dat')
    with open(rand_file_name, 'w') as fid:
        for i in range(nrand):
            fid.write(('%.20f %.20f\n')%(rx[i],ry[i]))
    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=0, rng=rng)
    rrr.process(rcat)
    zeta, varzeta = ddd.calculateZeta(rrr=rrr)

    # Semi-gratuitous check of Corr3.rng access.
    assert rrr.rng is rng
    assert ddd.rng is not rng

    # First do this via the corr3 function.
    config = treecorr.config.read_config('configs/nnn_direct.yaml')
    logger = treecorr.config.setup_logger(0)
    treecorr.corr3(config, logger)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_direct.out'), names=True,
                                    skip_header=1)
    np.testing.assert_allclose(corr3_output['r_nom'], ddd.rnom.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['u_nom'], ddd.u.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['v_nom'], ddd.v.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['DDD'], ddd.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['ntri'], ddd.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['RRR'], rrr.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['sigma_zeta'], np.sqrt(varzeta).flatten(), rtol=1.e-3)

    # Now calling out to the external corr3 executable.
    # This is the only time we test the corr3 executable.  All other tests use corr3 function.
    if os.name != 'nt':
        import subprocess
        corr3_exe = get_script_name('corr3')
        p = subprocess.Popen( [corr3_exe,"configs/nnn_direct.yaml","verbose=0"] )
        p.communicate()
        corr3_output = np.genfromtxt(os.path.join('output','nnn_direct.out'), names=True,
                                        skip_header=1)
        np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

    # Also check compensated
    drr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=0)
    rdd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=0)
    drr.process(cat, rcat)
    rdd.process(rcat, cat)
    zeta, varzeta = ddd.calculateZeta(rrr=rrr, drr=drr, rdd=rdd)

    config['nnn_statistic'] = 'compensated'
    treecorr.corr3(config, logger)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_direct.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['r_nom'], ddd.rnom.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['u_nom'], ddd.u.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['v_nom'], ddd.v.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['DDD'], ddd.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['ntri'], ddd.ntri.flatten(), rtol=1.e-3)
    rrrf = ddd.tot / rrr.tot
    drrf = ddd.tot / drr.tot
    rddf = ddd.tot / rdd.tot
    np.testing.assert_allclose(corr3_output['RRR'], rrr.ntri.flatten() * rrrf, rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['DRR'], drr.ntri.flatten() * drrf, rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['RDD'], rdd.ntri.flatten() * rddf, rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['sigma_zeta'], np.sqrt(varzeta).flatten(), rtol=1.e-3)

    # Repeat with binslop = 0, since the code flow is different from brute=True
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And compare to the cross correlation
    # Here, we get 6x as much, since each triangle is discovered 6 times.
    ddd.clear()
    ddd.process(cat,cat,cat, num_threads=2)
    np.testing.assert_array_equal(ddd.ntri, 6*true_ntri)

    # But with ordered=True, it only counts each triangle once.
    ddd.process(cat,cat,cat, ordered=True, num_threads=2)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Or with 2 argument version, finds each triangle 3 times.
    ddd.process(cat,cat)
    np.testing.assert_array_equal(ddd.ntri, 3*true_ntri)

    ddd.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    do_pickle(ddd)

    # Split into patches to test the list-based version of the code.
    cat = treecorr.Catalog(x=x, y=y, npatch=10)

    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    ddd.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    ddd.process(cat,cat, ordered=False)
    np.testing.assert_array_equal(ddd.ntri, 3*true_ntri)

    ddd.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    ddd.process(cat,cat,cat, ordered=False)
    np.testing.assert_array_equal(ddd.ntri, 6*true_ntri)

    # Invalid to omit file_name
    config['verbose'] = 0
    del config['file_name']
    with assert_raises(TypeError):
        treecorr.corr3(config)
    config['file_name'] = 'data/nnn_direct_data.dat'

    # OK to not have rand_file_name
    # Also, check the automatic setting of output_dots=True when verbose=2.
    # It's not too annoying if we also set max_top = 0.
    del config['rand_file_name']
    config['verbose'] = 2
    config['max_top'] = 0
    treecorr.corr3(config)
    data = np.genfromtxt(config['nnn_file_name'], names=True, skip_header=1)
    np.testing.assert_array_equal(data['ntri'], true_ntri.flatten())
    assert 'zeta' not in data.dtype.names

    # Check a few basic operations with a NNNCorrelation object.
    do_pickle(ddd)

    ddd2 = ddd.copy()
    ddd2 += ddd
    np.testing.assert_allclose(ddd2.ntri, 2*ddd.ntri)
    np.testing.assert_allclose(ddd2.weight, 2*ddd.weight)
    np.testing.assert_allclose(ddd2.meand1, 2*ddd.meand1)
    np.testing.assert_allclose(ddd2.meand2, 2*ddd.meand2)
    np.testing.assert_allclose(ddd2.meand3, 2*ddd.meand3)
    np.testing.assert_allclose(ddd2.meanlogd1, 2*ddd.meanlogd1)
    np.testing.assert_allclose(ddd2.meanlogd2, 2*ddd.meanlogd2)
    np.testing.assert_allclose(ddd2.meanlogd3, 2*ddd.meanlogd3)
    np.testing.assert_allclose(ddd2.meanu, 2*ddd.meanu)
    np.testing.assert_allclose(ddd2.meanv, 2*ddd.meanv)

    ddd2.clear()
    ddd2 += ddd
    np.testing.assert_allclose(ddd2.ntri, ddd.ntri)
    np.testing.assert_allclose(ddd2.weight, ddd.weight)
    np.testing.assert_allclose(ddd2.meand1, ddd.meand1)
    np.testing.assert_allclose(ddd2.meand2, ddd.meand2)
    np.testing.assert_allclose(ddd2.meand3, ddd.meand3)
    np.testing.assert_allclose(ddd2.meanlogd1, ddd.meanlogd1)
    np.testing.assert_allclose(ddd2.meanlogd2, ddd.meanlogd2)
    np.testing.assert_allclose(ddd2.meanlogd3, ddd.meanlogd3)
    np.testing.assert_allclose(ddd2.meanu, ddd.meanu)
    np.testing.assert_allclose(ddd2.meanv, ddd.meanv)

    ascii_name = 'output/nnn_ascii.txt'
    ddd.write(ascii_name, precision=16)
    ddd3 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    ddd3.read(ascii_name)
    np.testing.assert_allclose(ddd3.ntri, ddd.ntri)
    np.testing.assert_allclose(ddd3.weight, ddd.weight)
    np.testing.assert_allclose(ddd3.meand1, ddd.meand1)
    np.testing.assert_allclose(ddd3.meand2, ddd.meand2)
    np.testing.assert_allclose(ddd3.meand3, ddd.meand3)
    np.testing.assert_allclose(ddd3.meanlogd1, ddd.meanlogd1)
    np.testing.assert_allclose(ddd3.meanlogd2, ddd.meanlogd2)
    np.testing.assert_allclose(ddd3.meanlogd3, ddd.meanlogd3)
    np.testing.assert_allclose(ddd3.meanu, ddd.meanu)
    np.testing.assert_allclose(ddd3.meanv, ddd.meanv)

    with assert_raises(TypeError):
        ddd2 += config
    ddd4 = treecorr.NNNCorrelation(min_sep=min_sep/2, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd4
    ddd5 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep*2, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd5
    ddd6 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins*2,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd6
    ddd7 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u-0.1, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd7
    ddd8 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u+0.1, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd8
    ddd9 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins*2,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd9
    ddd10 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                    min_u=min_u, max_u=max_u, nubins=nubins,
                                    min_v=min_v-0.1, max_v=max_v, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd10
    ddd11 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                    min_u=min_u, max_u=max_u, nubins=nubins,
                                    min_v=min_v, max_v=max_v+0.1, nvbins=nvbins)
    with assert_raises(ValueError):
        ddd2 += ddd11
    ddd12 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                    min_u=min_u, max_u=max_u, nubins=nubins,
                                    min_v=min_v, max_v=max_v, nvbins=nvbins*2)
    with assert_raises(ValueError):
        ddd2 += ddd12

    # Check that adding results with different coords or metric emits a warning.
    cat2 = treecorr.Catalog(x=x, y=y, z=x)
    with CaptureLog() as cl:
        ddd13 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                        min_u=min_u, max_u=max_u, nubins=nubins,
                                        min_v=min_v, max_v=max_v, nvbins=nvbins,
                                        logger=cl.logger)
        ddd13.process_auto(cat2)
        ddd13 += ddd2
    assert "Detected a change in catalog coordinate systems" in cl.output

    with CaptureLog() as cl:
        ddd14 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                        min_u=min_u, max_u=max_u, nubins=nubins,
                                        min_v=min_v, max_v=max_v, nvbins=nvbins,
                                        logger=cl.logger)
        ddd14.process_auto(cat2, metric='Arc')
        ddd14 += ddd2
    assert "Detected a change in metric" in cl.output

    try:
        import fitsio
    except ImportError:
        pass
    else:
        fits_name = 'output/nnn_fits.fits'
        ddd.write(fits_name)
        ddd15 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                        min_u=min_u, max_u=max_u, nubins=nubins,
                                        min_v=min_v, max_v=max_v, nvbins=nvbins)
        ddd15.read(fits_name)
        np.testing.assert_allclose(ddd15.ntri, ddd.ntri)
        np.testing.assert_allclose(ddd15.weight, ddd.weight)
        np.testing.assert_allclose(ddd15.meand1, ddd.meand1)
        np.testing.assert_allclose(ddd15.meand2, ddd.meand2)
        np.testing.assert_allclose(ddd15.meand3, ddd.meand3)
        np.testing.assert_allclose(ddd15.meanlogd1, ddd.meanlogd1)
        np.testing.assert_allclose(ddd15.meanlogd2, ddd.meanlogd2)
        np.testing.assert_allclose(ddd15.meanlogd3, ddd.meanlogd3)
        np.testing.assert_allclose(ddd15.meanu, ddd.meanu)
        np.testing.assert_allclose(ddd15.meanv, ddd.meanv)

@timer
def test_direct_logruv_cross():
    # If the catalogs are small enough, we can do a direct count of the number of triangles
    # to see if comes out right.  This should exactly match the treecorr code if brute=True

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    cat3 = treecorr.Catalog(x=x3, y=y3)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=1)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('brute unordered: ',t1-t0)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_123 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_132 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_213 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_231 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_312 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_321 = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(ngal):
        for j in range(ngal):
            for k in range(ngal):
                dij = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2)
                dik = np.sqrt((x1[i]-x3[k])**2 + (y1[i]-y3[k])**2)
                djk = np.sqrt((x2[j]-x3[k])**2 + (y2[j]-y3[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x2[j],y2[j],x3[k],y3[k])
                        true_ntri = true_ntri_123
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x1[i],y1[i],x3[k],y3[k])
                        true_ntri = true_ntri_213
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x3[k],y3[k],x1[i],y1[i])
                        true_ntri = true_ntri_231
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j])
                        true_ntri = true_ntri_132
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x1[i],y1[i],x2[j],y2[j])
                        true_ntri = true_ntri_312
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x2[j],y2[j],x1[i],y1[i])
                        true_ntri = true_ntri_321

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = true_ntri_123 + true_ntri_132 + true_ntri_213 + true_ntri_231 +\
            true_ntri_312 + true_ntri_321
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    # With ordered=True we get just the ones in the given order.
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('brute ordered 123: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)
    t0 = time.time()
    ddd.process(cat1, cat3, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 132: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_132)
    t0 = time.time()
    ddd.process(cat2, cat1, cat3, ordered=True)
    t1 = time.time()
    print('brute ordered 213: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_213)
    t0 = time.time()
    ddd.process(cat2, cat3, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 231: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_231)
    t0 = time.time()
    ddd.process(cat3, cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 312: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_312)
    t0 = time.time()
    ddd.process(cat3, cat2, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 321: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_321)

    # Repeat with binslop = 0
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('bin_slop=0 unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 123: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)
    t0 = time.time()
    ddd.process(cat1, cat3, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 132: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_132)
    t0 = time.time()
    ddd.process(cat2, cat1, cat3, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 213: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_213)
    t0 = time.time()
    ddd.process(cat2, cat3, cat1, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 231: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_231)
    t0 = time.time()
    ddd.process(cat3, cat1, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 312: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_312)
    t0 = time.time()
    ddd.process(cat3, cat2, cat1, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 321: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_321)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('no top bin_slop=0, ordered 123 ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    # Error to have cat3, but not cat2
    with assert_raises(ValueError):
        ddd.process(cat1, cat3=cat3)


@timer
def test_direct_logruv_cross12():
    # Check the 1-2 cross correlation

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=1)
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('brute: ',t1-t0)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_122 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_212 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_221 = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(ngal):
        for j in range(ngal):
            for k in range(j+1,ngal):
                dij = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2)
                dik = np.sqrt((x1[i]-x2[k])**2 + (y1[i]-y2[k])**2)
                djk = np.sqrt((x2[j]-x2[k])**2 + (y2[j]-y2[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x2[j],y2[j],x2[k],y2[k])
                        true_ntri = true_ntri_122
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x1[i],y1[i],x2[k],y2[k])
                        true_ntri = true_ntri_212
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x2[k],y2[k],x1[i],y1[i])
                        true_ntri = true_ntri_221
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j])
                        true_ntri = true_ntri_122
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x2[k],y2[k],x1[i],y1[i],x2[j],y2[j])
                        true_ntri = true_ntri_212
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x2[k],y2[k],x2[j],y2[j],x1[i],y1[i])
                        true_ntri = true_ntri_221

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = true_ntri_122 + true_ntri_212 + true_ntri_221
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    # With ordered=True we get just the ones in the given order.
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

    # Repeat with binslop = 0
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('bin_slop=0 unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('no top bin_slop=0 unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    # Split into patches to test the list-based version of the code.
    cat1 = treecorr.Catalog(x=x1, y=y1, npatch=10)
    cat2 = treecorr.Catalog(x=x2, y=y2, npatch=10)

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('patch unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('patch ordered 122: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)


@timer
def test_direct_logruv_spherical():
    # Repeat in spherical coords

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) ) + 200  # Put everything at large y, so small angle on sky
    z = rng.normal(0,s, (ngal,) )
    w = rng.random_sample(ngal)

    ra, dec = coord.CelestialCoord.xyz_to_radec(x,y,z)

    cat = treecorr.Catalog(ra=ra, dec=dec, ra_units='rad', dec_units='rad', w=w)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    nubins = 5
    nvbins = 5
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  sep_units='deg', brute=True)
    ddd.process(cat, num_threads=2)

    r = np.sqrt(x**2 + y**2 + z**2)
    x /= r;  y /= r;  z /= r

    true_ntri = np.zeros((nrbins, nubins, 2*nvbins), dtype=int)
    true_weight = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)

    rad_min_sep = min_sep * coord.degrees / coord.radians
    for i in range(ngal):
        for j in range(i+1,ngal):
            for k in range(j+1,ngal):
                d12 = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2 + (z[i]-z[j])**2)
                d23 = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2 + (z[j]-z[k])**2)
                d31 = np.sqrt((x[k]-x[i])**2 + (y[k]-y[i])**2 + (z[k]-z[i])**2)

                d3, d2, d1 = sorted([d12, d23, d31])
                rindex = np.floor(np.log(d2/rad_min_sep) / bin_size).astype(int)
                if rindex < 0 or rindex >= nrbins: continue

                if [d1, d2, d3] == [d23, d31, d12]: ii,jj,kk = i,j,k
                elif [d1, d2, d3] == [d23, d12, d31]: ii,jj,kk = i,k,j
                elif [d1, d2, d3] == [d31, d12, d23]: ii,jj,kk = j,k,i
                elif [d1, d2, d3] == [d31, d23, d12]: ii,jj,kk = j,i,k
                elif [d1, d2, d3] == [d12, d23, d31]: ii,jj,kk = k,i,j
                elif [d1, d2, d3] == [d12, d31, d23]: ii,jj,kk = k,j,i
                else: assert False
                # Now use ii, jj, kk rather than i,j,k, to get the indices
                # that correspond to the points in the right order.

                u = d3/d2
                v = (d1-d2)/d3
                if ( ((x[jj]-x[ii])*(y[kk]-y[ii]) - (x[kk]-x[ii])*(y[jj]-y[ii])) * z[ii] +
                     ((y[jj]-y[ii])*(z[kk]-z[ii]) - (y[kk]-y[ii])*(z[jj]-z[ii])) * x[ii] +
                     ((z[jj]-z[ii])*(x[kk]-x[ii]) - (z[kk]-z[ii])*(x[jj]-x[ii])) * y[ii] ) > 0:
                    v = -v

                uindex = np.floor(u / bin_size).astype(int)
                assert 0 <= uindex < nubins
                vindex = np.floor((v+1) / bin_size).astype(int)
                assert 0 <= vindex < 2*nvbins

                www = w[i] * w[j] * w[k]
                true_ntri[rindex,uindex,vindex] += 1
                true_weight[rindex,uindex,vindex] += www

    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    np.testing.assert_allclose(ddd.weight, true_weight, rtol=1.e-5, atol=1.e-8)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/nnn_direct_spherical.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['nnn_file_name'])
        np.testing.assert_allclose(data['r_nom'], ddd.rnom.flatten())
        np.testing.assert_allclose(data['u_nom'], ddd.u.flatten())
        np.testing.assert_allclose(data['v_nom'], ddd.v.flatten())
        np.testing.assert_allclose(data['ntri'], ddd.ntri.flatten())
        np.testing.assert_allclose(data['DDD'], ddd.weight.flatten())

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  sep_units='deg', bin_slop=0, max_top=0)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    np.testing.assert_allclose(ddd.weight, true_weight, rtol=1.e-5, atol=1.e-8)


@timer
def test_direct_logruv_arc():
    # Repeat the spherical test with metric='Arc'

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) ) + 200  # Large angles this time.
    z = rng.normal(0,s, (ngal,) )
    w = rng.random_sample(ngal)

    ra, dec = coord.CelestialCoord.xyz_to_radec(x,y,z)

    cat = treecorr.Catalog(ra=ra, dec=dec, ra_units='rad', dec_units='rad', w=w)

    min_sep = 1.
    max_sep = 180.
    nrbins = 10
    nubins = 5
    nvbins = 5
    bin_size = np.log((max_sep / min_sep)) / nrbins
    ubin_size = 0.2
    vbin_size = 0.2
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  nubins=nubins, ubin_size=ubin_size,
                                  nvbins=nvbins, vbin_size=vbin_size,
                                  sep_units='deg', brute=True)
    ddd.process(cat, metric='Arc')

    r = np.sqrt(x**2 + y**2 + z**2)
    x /= r;  y /= r;  z /= r

    true_ntri = np.zeros((nrbins, nubins, 2*nvbins), dtype=int)
    true_weight = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)

    c = [coord.CelestialCoord(r*coord.radians, d*coord.radians) for (r,d) in zip(ra, dec)]
    for i in range(ngal):
        for j in range(i+1,ngal):
            for k in range(j+1,ngal):
                d12 = c[i].distanceTo(c[j]) / coord.degrees
                d23 = c[j].distanceTo(c[k]) / coord.degrees
                d31 = c[k].distanceTo(c[i]) / coord.degrees

                d3, d2, d1 = sorted([d12, d23, d31])
                rindex = np.floor(np.log(d2/min_sep) / bin_size).astype(int)
                if rindex < 0 or rindex >= nrbins: continue

                if [d1, d2, d3] == [d23, d31, d12]: ii,jj,kk = i,j,k
                elif [d1, d2, d3] == [d23, d12, d31]: ii,jj,kk = i,k,j
                elif [d1, d2, d3] == [d31, d12, d23]: ii,jj,kk = j,k,i
                elif [d1, d2, d3] == [d31, d23, d12]: ii,jj,kk = j,i,k
                elif [d1, d2, d3] == [d12, d23, d31]: ii,jj,kk = k,i,j
                elif [d1, d2, d3] == [d12, d31, d23]: ii,jj,kk = k,j,i
                else: assert False
                # Now use ii, jj, kk rather than i,j,k, to get the indices
                # that correspond to the points in the right order.

                u = d3/d2
                v = (d1-d2)/d3
                if ( ((x[jj]-x[ii])*(y[kk]-y[ii]) - (x[kk]-x[ii])*(y[jj]-y[ii])) * z[ii] +
                     ((y[jj]-y[ii])*(z[kk]-z[ii]) - (y[kk]-y[ii])*(z[jj]-z[ii])) * x[ii] +
                     ((z[jj]-z[ii])*(x[kk]-x[ii]) - (z[kk]-z[ii])*(x[jj]-x[ii])) * y[ii] ) > 0:
                    v = -v

                uindex = np.floor(u / ubin_size).astype(int)
                assert 0 <= uindex < nubins
                vindex = np.floor((v+1) / vbin_size).astype(int)
                assert 0 <= vindex < 2*nvbins

                www = w[i] * w[j] * w[k]
                true_ntri[rindex,uindex,vindex] += 1
                true_weight[rindex,uindex,vindex] += www

    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    np.testing.assert_allclose(ddd.weight, true_weight, rtol=1.e-5, atol=1.e-8)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/nnn_direct_arc.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['nnn_file_name'])
        np.testing.assert_allclose(data['r_nom'], ddd.rnom.flatten())
        np.testing.assert_allclose(data['u_nom'], ddd.u.flatten())
        np.testing.assert_allclose(data['v_nom'], ddd.v.flatten())
        np.testing.assert_allclose(data['ntri'], ddd.ntri.flatten())
        np.testing.assert_allclose(data['DDD'], ddd.weight.flatten())

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  nubins=nubins, ubin_size=ubin_size,
                                  nvbins=nvbins, vbin_size=vbin_size,
                                  sep_units='deg', bin_slop=0, max_top=0)
    ddd.process(cat, metric='Arc')
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    np.testing.assert_allclose(ddd.weight, true_weight, rtol=1.e-5, atol=1.e-8)


@timer
def test_direct_logruv_partial():
    # Test the two ways to only use parts of a catalog:

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 100
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    cat1a = treecorr.Catalog(x=x1, y=y1, first_row=28, last_row=84)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    cat2a = treecorr.Catalog(x=x2, y=y2, first_row=48, last_row=99)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    cat3a = treecorr.Catalog(x=x3, y=y3, first_row=22, last_row=67)

    min_sep = 1.
    max_sep = 50.
    nbins = 50
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10

    ddda = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins,
                                   brute=True)
    ddda.process(cat1a, cat2a, cat3a)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_123 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_132 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_213 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_231 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_312 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_321 = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(27,84):
        for j in range(47,99):
            for k in range(21,67):
                dij = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2)
                dik = np.sqrt((x1[i]-x3[k])**2 + (y1[i]-y3[k])**2)
                djk = np.sqrt((x2[j]-x3[k])**2 + (y2[j]-y3[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x2[j],y2[j],x3[k],y3[k])
                        true_ntri = true_ntri_123
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x1[i],y1[i],x3[k],y3[k])
                        true_ntri = true_ntri_213
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x3[k],y3[k],x1[i],y1[i])
                        true_ntri = true_ntri_231
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j])
                        true_ntri = true_ntri_132
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x1[i],y1[i],x2[j],y2[j])
                        true_ntri = true_ntri_312
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x2[j],y2[j],x1[i],y1[i])
                        true_ntri = true_ntri_321
                assert d1 >= d2 >= d3

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    true_ntri_sum = true_ntri_123 + true_ntri_132 + true_ntri_213 + true_ntri_231 +\
            true_ntri_312 + true_ntri_321
    np.testing.assert_array_equal(ddda.ntri, true_ntri_sum)

    ddda.process(cat1a, cat2a, cat3a, ordered=True)
    np.testing.assert_array_equal(ddda.ntri, true_ntri_123)

    # Now check that we get the same thing with all the points, but with w=0 for the ones
    # we don't want.
    w1 = np.zeros(ngal)
    w1[27:84] = 1.
    w2 = np.zeros(ngal)
    w2[47:99] = 1.
    w3 = np.zeros(ngal)
    w3[21:67] = 1.
    cat1b = treecorr.Catalog(x=x1, y=y1, w=w1)
    cat2b = treecorr.Catalog(x=x2, y=y2, w=w2)
    cat3b = treecorr.Catalog(x=x3, y=y3, w=w3)
    dddb = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, nubins=nubins,
                                   min_v=min_v, max_v=max_v, nvbins=nvbins,
                                   brute=True)
    dddb.process(cat1b, cat2b, cat3b)
    np.testing.assert_array_equal(dddb.ntri, true_ntri_sum)

    dddb.process(cat1b, cat2b, cat3b, ordered=True)
    np.testing.assert_array_equal(dddb.ntri, true_ntri_123)


@timer
def test_direct_logruv_3d_auto():
    # This is the same as test_direct_count_auto, but using the 3d correlations

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(312, s, (ngal,) )
    y = rng.normal(728, s, (ngal,) )
    z = rng.normal(-932, s, (ngal,) )
    r = np.sqrt( x*x + y*y + z*z )
    dec = np.arcsin(z/r)
    ra = np.arctan2(y,x)
    cat = treecorr.Catalog(ra=ra, dec=dec, r=r, ra_units='rad', dec_units='rad')

    min_sep = 1.
    max_sep = 50.
    nbins = 50
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=1)
    ddd.process(cat)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(ngal):
        for j in range(i+1,ngal):
            for k in range(j+1,ngal):
                dij = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2 + (z[i]-z[j])**2)
                dik = np.sqrt((x[i]-x[k])**2 + (y[i]-y[k])**2 + (z[i]-z[k])**2)
                djk = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2 + (z[j]-z[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw_3d(x[i],y[i],z[i],x[j],y[j],z[j],x[k],y[k],z[k])
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw_3d(x[j],y[j],z[j],x[i],y[i],z[i],x[k],y[k],z[k])
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw_3d(x[j],y[j],z[j],x[k],y[k],z[k],x[i],y[i],z[i])
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw_3d(x[i],y[i],z[i],x[k],y[k],z[k],x[j],y[j],z[j])
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw_3d(x[k],y[k],z[k],x[i],y[i],z[i],x[j],y[j],z[j])
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw_3d(x[k],y[k],z[k],x[j],y[j],z[j],x[i],y[i],z[i])

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Repeat with binslop = 0
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And compare to the cross correlation
    # With ordered=False, we get 6x as much, since each triangle is discovered 6 times.
    ddd.process(cat,cat,cat)
    np.testing.assert_array_equal(ddd.ntri, 6*true_ntri)

    ddd.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Also compare to using x,y,z rather than ra,dec,r
    cat = treecorr.Catalog(x=x, y=y, z=z)
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)


@timer
def test_direct_logruv_3d_cross():
    # This is the same as test_direct_count_cross, but using the 3d correlations

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(312, s, (ngal,) )
    y1 = rng.normal(728, s, (ngal,) )
    z1 = rng.normal(-932, s, (ngal,) )
    r1 = np.sqrt( x1*x1 + y1*y1 + z1*z1 )
    dec1 = np.arcsin(z1/r1)
    ra1 = np.arctan2(y1,x1)
    cat1 = treecorr.Catalog(ra=ra1, dec=dec1, r=r1, ra_units='rad', dec_units='rad')

    x2 = rng.normal(312, s, (ngal,) )
    y2 = rng.normal(728, s, (ngal,) )
    z2 = rng.normal(-932, s, (ngal,) )
    r2 = np.sqrt( x2*x2 + y2*y2 + z2*z2 )
    dec2 = np.arcsin(z2/r2)
    ra2 = np.arctan2(y2,x2)
    cat2 = treecorr.Catalog(ra=ra2, dec=dec2, r=r2, ra_units='rad', dec_units='rad')

    x3 = rng.normal(312, s, (ngal,) )
    y3 = rng.normal(728, s, (ngal,) )
    z3 = rng.normal(-932, s, (ngal,) )
    r3 = np.sqrt( x3*x3 + y3*y3 + z3*z3 )
    dec3 = np.arcsin(z3/r3)
    ra3 = np.arctan2(y3,x3)
    cat3 = treecorr.Catalog(ra=ra3, dec=dec3, r=r3, ra_units='rad', dec_units='rad')

    min_sep = 1.
    max_sep = 50.
    nbins = 50
    min_u = 0.13
    max_u = 0.89
    nubins = 10
    min_v = 0.13
    max_v = 0.59
    nvbins = 10
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True, verbose=1)
    ddd.process(cat1, cat2, cat3)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_123 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_132 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_213 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_231 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_312 = np.zeros( (nbins, nubins, 2*nvbins) )
    true_ntri_321 = np.zeros( (nbins, nubins, 2*nvbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    for i in range(ngal):
        for j in range(ngal):
            for k in range(ngal):
                djk = np.sqrt((x2[j]-x3[k])**2 + (y2[j]-y3[k])**2 + (z2[j]-z3[k])**2)
                dik = np.sqrt((x1[i]-x3[k])**2 + (y1[i]-y3[k])**2 + (z1[i]-z3[k])**2)
                dij = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2 + (z1[i]-z2[j])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw_3d(x1[i],y1[i],z1[i],x2[j],y2[j],z2[j],x3[k],y3[k],z3[k])
                        true_ntri = true_ntri_123
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw_3d(x2[j],y2[j],z2[j],x1[i],y1[i],z1[i],x3[k],y3[k],z3[k])
                        true_ntri = true_ntri_213
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw_3d(x2[j],y2[j],z2[j],x3[k],y3[k],z3[k],x1[i],y1[i],z1[i])
                        true_ntri = true_ntri_231
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw_3d(x1[i],y1[i],z1[i],x3[k],y3[k],z3[k],x2[j],y2[j],z2[j])
                        true_ntri = true_ntri_132
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw_3d(x3[k],y3[k],z3[k],x1[i],y1[i],z1[i],x2[j],y2[j],z2[j])
                        true_ntri = true_ntri_312
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw_3d(x3[k],y3[k],z3[k],x2[j],y2[j],z2[j],x1[i],y1[i],z1[i])
                        true_ntri = true_ntri_321

                r = d2
                u = d3/d2
                v = (d1-d2)/d3
                if r < min_sep or r >= max_sep: continue
                if u < min_u or u >= max_u: continue
                if v < min_v or v >= max_v: continue
                if not ccw:
                    v = -v
                kr = int(np.floor( (np.log(r)-log_min_sep) / bin_size ))
                ku = int(np.floor( (u-min_u) / ubin_size ))
                if v > 0:
                    kv = int(np.floor( (v-min_v) / vbin_size )) + nvbins
                else:
                    kv = int(np.floor( (v-(-max_v)) / vbin_size ))
                assert 0 <= kr < nbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                true_ntri[kr,ku,kv] += 1

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = true_ntri_123 + true_ntri_132 + true_ntri_213 + true_ntri_231 +\
            true_ntri_312 + true_ntri_321
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    ddd.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    ddd.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    ddd.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    ddd.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    ddd.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    # Also compare to using x,y,z rather than ra,dec,r
    cat1 = treecorr.Catalog(x=x1, y=y1, z=z1)
    cat2 = treecorr.Catalog(x=x2, y=y2, z=z2)
    cat3 = treecorr.Catalog(x=x3, y=y3, z=z3)
    ddd.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    ddd.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)


@timer
def test_nnn_logruv():
    # Use a simple probability distribution for the galaxies:
    #
    # n(r) = (2pi s^2)^-1 exp(-r^2/2s^2)
    #
    # The Fourier transform is: n~(k) = exp(-s^2 k^2/2)
    # B(k1,k2) = <n~(k1) n~(k2) n~(-k1-k2)>
    #          = exp(-s^2 (|k1|^2 + |k2|^2 - k1.k2))
    #          = exp(-s^2 (|k1|^2 + |k2|^2 + |k3|^2)/2)
    #
    # zeta(r1,r2) = (1/2pi)^4 int(d^2k1 int(d^2k2 exp(ik1.x1) exp(ik2.x2) B(k1,k2) ))
    #             = exp(-(x1^2 + y1^2 + x2^2 + y2^2 - x1x2 - y1y2)/3s^2) / 12 pi^2 s^4
    #             = exp(-(d1^2 + d2^2 + d3^2)/6s^2) / 12 pi^2 s^4
    #
    # This is also derivable as:
    # zeta(r1,r2) = int(dx int(dy n(x,y) n(x+x1,y+y1) n(x+x2,y+y2)))
    # which is also analytically integrable and gives the same answer.
    #
    # However, we need to correct for the uniform density background, so the real result
    # is this minus 1/L^4 divided by 1/L^4.  So:
    #
    # zeta(r1,r2) = 1/(12 pi^2) (L/s)^4 exp(-(d1^2+d2^2+d3^2)/6s^2) - 1

    # Doing the full correlation function takes a long time.  Here, we just test a small range
    # of separations and a moderate range for u, v, which gives us a variety of triangle lengths.
    s = 10.
    if __name__ == "__main__":
        ngal = 20000
        nrand = 2 * ngal
        L = 50. * s  # Not infinity, so this introduces some error.  Our integrals were to infinity.
        tol_factor = 1
    else:
        ngal = 2000
        nrand = ngal
        L = 20. * s
        tol_factor = 5

    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    min_sep = 11.
    max_sep = 13.
    nbins = 2
    min_u = 0.6
    max_u = 0.9
    nubins = 3
    min_v = 0.5
    max_v = 0.9
    nvbins = 5

    cat = treecorr.Catalog(x=x, y=y, x_units='arcmin', y_units='arcmin')
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins,
                                  sep_units='arcmin', verbose=1)
    ddd.process(cat)

    # Using bin_size=None rather than omitting bin_size is equivalent.
    ddd2 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins, bin_size=None,
                                   min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                   nubins=nubins, nvbins=nvbins,
                                   sep_units='arcmin', verbose=1)
    ddd2.process(cat, num_threads=1)
    ddd.process(cat, num_threads=1)
    assert ddd2 == ddd

    # log(<d>) != <logd>, but it should be close:
    print('meanlogd1 - log(meand1) = ',ddd.meanlogd1 - np.log(ddd.meand1))
    print('meanlogd2 - log(meand2) = ',ddd.meanlogd2 - np.log(ddd.meand2))
    print('meanlogd3 - log(meand3) = ',ddd.meanlogd3 - np.log(ddd.meand3))
    print('meand3 / meand2 = ',ddd.meand3 / ddd.meand2)
    print('meanu = ',ddd.meanu)
    print('max diff = ',np.max(np.abs(ddd.meand3/ddd.meand2 -ddd.meanu)))
    print('max rel diff = ',np.max(np.abs((ddd.meand3/ddd.meand2 -ddd.meanu)/ddd.meanu)))
    print('(meand1 - meand2)/meand3 = ',(ddd.meand1-ddd.meand2) / ddd.meand3)
    print('meanv = ',ddd.meanv)
    print('max diff = ',np.max(np.abs((ddd.meand1-ddd.meand2)/ddd.meand3 -np.abs(ddd.meanv))))
    print('max rel diff = ',
          np.max(np.abs(((ddd.meand1-ddd.meand2)/ddd.meand3-np.abs(ddd.meanv))/ddd.meanv)))
    np.testing.assert_allclose(ddd.meanlogd1, np.log(ddd.meand1), rtol=1.e-3)
    np.testing.assert_allclose(ddd.meanlogd2, np.log(ddd.meand2), rtol=1.e-3)
    np.testing.assert_allclose(ddd.meanlogd3, np.log(ddd.meand3), rtol=1.e-3)
    np.testing.assert_allclose(ddd.meand3/ddd.meand2, ddd.meanu, rtol=1.e-5 * tol_factor)
    np.testing.assert_allclose((ddd.meand1-ddd.meand2)/ddd.meand3, np.abs(ddd.meanv),
                                  rtol=1.e-5 * tol_factor, atol=1.e-5 * tol_factor)
    np.testing.assert_allclose(ddd.meanlogd3-ddd.meanlogd2, np.log(ddd.meanu),
                                  atol=1.e-3 * tol_factor)
    np.testing.assert_allclose(np.log(ddd.meand1-ddd.meand2)-ddd.meanlogd3,
                                  np.log(np.abs(ddd.meanv)), atol=2.e-3 * tol_factor)

    rx = (rng.random_sample(nrand)-0.5) * L
    ry = (rng.random_sample(nrand)-0.5) * L
    rand = treecorr.Catalog(x=rx,y=ry, x_units='arcmin', y_units='arcmin')
    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins,
                                  sep_units='arcmin', verbose=1)
    rrr.process(rand)

    d1 = ddd.meand1
    d2 = ddd.meand2
    d3 = ddd.meand3
    true_zeta = (1./(12.*np.pi**2)) * (L/s)**4 * np.exp(-(d1**2+d2**2+d3**2)/(6.*s**2)) - 1.

    zeta, varzeta = ddd.calculateZeta(rrr=rrr)
    print('zeta = ',zeta)
    print('true_zeta = ',true_zeta)
    print('ratio = ',zeta / true_zeta)
    print('diff = ',zeta - true_zeta)
    print('max rel diff = ',np.max(np.abs((zeta - true_zeta)/true_zeta)))
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)),
                                  atol=0.1*tol_factor)

    # Check that we get the same result using the corr3 function
    cat.write(os.path.join('data','nnn_data.dat'))
    rand.write(os.path.join('data','nnn_rand.dat'))
    config = treecorr.config.read_config('configs/nnn.yaml')
    config['verbose'] = 0
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn.out'), names=True, skip_header=1)
    print('zeta = ',zeta)
    print('from corr3 output = ',corr3_output['zeta'])
    print('ratio = ',corr3_output['zeta']/zeta.flatten())
    print('diff = ',corr3_output['zeta']-zeta.flatten())
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

    # Check the fits write option
    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name1 = os.path.join('output','nnn_out1.fits')
        ddd.write(out_file_name1)
        data = fitsio.read(out_file_name1)
        np.testing.assert_almost_equal(data['r_nom'], np.exp(ddd.logr).flatten())
        np.testing.assert_almost_equal(data['u_nom'], ddd.u.flatten())
        np.testing.assert_almost_equal(data['v_nom'], ddd.v.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanu'], ddd.meanu.flatten())
        np.testing.assert_almost_equal(data['meanv'], ddd.meanv.flatten())
        np.testing.assert_almost_equal(data['ntri'], ddd.ntri.flatten())
        header = fitsio.read_header(out_file_name1, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        out_file_name2 = os.path.join('output','nnn_out2.fits')
        ddd.write(out_file_name2, rrr=rrr)
        data = fitsio.read(out_file_name2)
        np.testing.assert_almost_equal(data['r_nom'], np.exp(ddd.logr).flatten())
        np.testing.assert_almost_equal(data['u_nom'], ddd.u.flatten())
        np.testing.assert_almost_equal(data['v_nom'], ddd.v.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanu'], ddd.meanu.flatten())
        np.testing.assert_almost_equal(data['meanv'], ddd.meanv.flatten())
        np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        header = fitsio.read_header(out_file_name2, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        # Check the read function
        # Note: These don't need the flatten.
        # The read function should reshape them to the right shape.
        ddd2 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                       nubins=nubins, nvbins=nvbins,
                                       sep_units='arcmin', verbose=1)
        ddd2.read(out_file_name1)
        np.testing.assert_almost_equal(ddd2.logr, ddd.logr)
        np.testing.assert_almost_equal(ddd2.u, ddd.u)
        np.testing.assert_almost_equal(ddd2.v, ddd.v)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanu, ddd.meanu)
        np.testing.assert_almost_equal(ddd2.meanv, ddd.meanv)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

        ddd2.read(out_file_name2)
        np.testing.assert_almost_equal(ddd2.logr, ddd.logr)
        np.testing.assert_almost_equal(ddd2.u, ddd.u)
        np.testing.assert_almost_equal(ddd2.v, ddd.v)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanu, ddd.meanu)
        np.testing.assert_almost_equal(ddd2.meanv, ddd.meanv)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

    # Check the hdf5 write option
    try:
        import h5py  # noqa: F401
    except ImportError:
        pass
    else:
        out_file_name3 = os.path.join('output','nnn_out3.hdf5')
        ddd.write(out_file_name3, rrr=rrr)
        with h5py.File(out_file_name3, 'r') as hdf:
            data = hdf['/']
            np.testing.assert_almost_equal(data['r_nom'], np.exp(ddd.logr).flatten())
            np.testing.assert_almost_equal(data['u_nom'], ddd.u.flatten())
            np.testing.assert_almost_equal(data['v_nom'], ddd.v.flatten())
            np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
            np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
            np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
            np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
            np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
            np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
            np.testing.assert_almost_equal(data['meanu'], ddd.meanu.flatten())
            np.testing.assert_almost_equal(data['meanv'], ddd.meanv.flatten())
            np.testing.assert_almost_equal(data['ntri'], ddd.ntri.flatten())
            np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
            np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
            np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
            np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
            attrs = data.attrs
            np.testing.assert_almost_equal(attrs['tot']/ddd.tot, 1.)

        ddd3 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                       nubins=nubins, nvbins=nvbins,
                                       sep_units='arcmin', verbose=1)
        ddd3.read(out_file_name3)
        np.testing.assert_almost_equal(ddd3.logr, ddd.logr)
        np.testing.assert_almost_equal(ddd3.u, ddd.u)
        np.testing.assert_almost_equal(ddd3.v, ddd.v)
        np.testing.assert_almost_equal(ddd3.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd3.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd3.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd3.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd3.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd3.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd3.meanu, ddd.meanu)
        np.testing.assert_almost_equal(ddd3.meanv, ddd.meanv)
        np.testing.assert_almost_equal(ddd3.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd3.tot/ddd.tot, 1.)
        assert ddd3.coords == ddd.coords
        assert ddd3.metric == ddd.metric
        assert ddd3.sep_units == ddd.sep_units
        assert ddd3.bin_type == ddd.bin_type

    # Test compensated zeta
    # First just check the mechanics.
    # If we don't actually do all the cross terms, then compensated is the same as simple.
    zeta2, varzeta2 = ddd.calculateZeta(rrr=rrr, drr=rrr, rdd=rrr)
    print('fake compensated zeta = ',zeta2)
    np.testing.assert_allclose(zeta2, zeta)

    # Error to not have one of rrr, drr, rdd.
    with assert_raises(TypeError):
        ddd.calculateZeta(drr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.calculateZeta(rrr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.calculateZeta(rrr=rrr, drr=rrr)
    rrr2 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                   nubins=nubins, nvbins=nvbins, sep_units='arcmin')
    # Error if any of them haven't been run yet.
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr2, drr=rrr, rdd=rrr)
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr, drr=rrr2, rdd=rrr)
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr, drr=rrr, rdd=rrr2)

    out_file_name3 = os.path.join('output','nnn_out3.dat')
    with assert_raises(TypeError):
        ddd.write(out_file_name3, drr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.write(out_file_name3, rrr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.write(out_file_name3, rrr=rrr, drr=rrr)

    # This version computes the three-point function after subtracting off the appropriate
    # two-point functions xi(d1) + xi(d2) + xi(d3), where [cf. test_nn() in test_nn.py]
    # xi(r) = 1/4pi (L/s)^2 exp(-r^2/4s^2) - 1
    drr = ddd.copy()
    rdd = ddd.copy()

    drr.process(cat,rand)
    rdd.process(rand,cat)

    zeta, varzeta = ddd.calculateZeta(rrr=rrr, drr=drr, rdd=rdd)
    print('compensated zeta = ',zeta)

    xi1 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d1**2/(4.*s**2)) - 1.
    xi2 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d2**2/(4.*s**2)) - 1.
    xi3 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d3**2/(4.*s**2)) - 1.
    print('xi1 = ',xi1)
    print('xi2 = ',xi2)
    print('xi3 = ',xi3)
    print('true_zeta + xi1 + xi2 + xi3 = ',true_zeta)
    true_zeta -= xi1 + xi2 + xi3
    print('true_zeta => ',true_zeta)
    print('ratio = ',zeta / true_zeta)
    print('diff = ',zeta - true_zeta)
    print('max rel diff = ',np.max(np.abs((zeta - true_zeta)/true_zeta)))
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)), atol=0.1*tol_factor)

    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name3 = os.path.join('output','nnn_out3.fits')
        ddd.write(out_file_name3, rrr=rrr, drr=drr, rdd=rdd)
        data = fitsio.read(out_file_name3)
        np.testing.assert_almost_equal(data['r_nom'], np.exp(ddd.logr).flatten())
        np.testing.assert_almost_equal(data['u_nom'], ddd.u.flatten())
        np.testing.assert_almost_equal(data['v_nom'], ddd.v.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanu'], ddd.meanu.flatten())
        np.testing.assert_almost_equal(data['meanv'], ddd.meanv.flatten())
        np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        np.testing.assert_almost_equal(data['DRR'], drr.ntri.flatten() * (ddd.tot / drr.tot))
        np.testing.assert_almost_equal(data['RDD'], rdd.ntri.flatten() * (ddd.tot / rdd.tot))
        header = fitsio.read_header(out_file_name3, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        ddd2.read(out_file_name3)
        np.testing.assert_almost_equal(ddd2.logr, ddd.logr)
        np.testing.assert_almost_equal(ddd2.u, ddd.u)
        np.testing.assert_almost_equal(ddd2.v, ddd.v)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanu, ddd.meanu)
        np.testing.assert_almost_equal(ddd2.meanv, ddd.meanv)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

        config = treecorr.config.read_config('configs/nnn_compensated.yaml')
        config['verbose'] = 0
        treecorr.corr3(config)
        corr3_outfile = os.path.join('output','nnn_compensated.fits')
        corr3_output = fitsio.read(corr3_outfile)
        print('zeta = ',zeta)
        print('from corr3 output = ',corr3_output['zeta'])
        print('ratio = ',corr3_output['zeta']/zeta.flatten())
        print('diff = ',corr3_output['zeta']-zeta.flatten())

        np.testing.assert_almost_equal(corr3_output['r_nom'], np.exp(ddd.logr).flatten())
        np.testing.assert_almost_equal(corr3_output['u_nom'], ddd.u.flatten())
        np.testing.assert_almost_equal(corr3_output['v_nom'], ddd.v.flatten())
        np.testing.assert_almost_equal(corr3_output['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(corr3_output['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(corr3_output['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(corr3_output['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(corr3_output['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(corr3_output['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(corr3_output['meanu'], ddd.meanu.flatten())
        np.testing.assert_almost_equal(corr3_output['meanv'], ddd.meanv.flatten())
        np.testing.assert_almost_equal(corr3_output['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(corr3_output['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(corr3_output['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(corr3_output['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        np.testing.assert_almost_equal(corr3_output['DRR'], drr.ntri.flatten() * (ddd.tot / drr.tot))
        np.testing.assert_almost_equal(corr3_output['RDD'], rdd.ntri.flatten() * (ddd.tot / rdd.tot))
        header = fitsio.read_header(corr3_outfile, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)



@timer
def test_3d_logruv():
    # For this one, build a Gaussian cloud around some random point in 3D space and do the
    # correlation function in 3D.
    #
    # The 3D Fourier transform is: n~(k) = exp(-s^2 k^2/2)
    # B(k1,k2) = <n~(k1) n~(k2) n~(-k1-k2)>
    #          = exp(-s^2 (|k1|^2 + |k2|^2 - k1.k2))
    #          = exp(-s^2 (|k1|^2 + |k2|^2 + |k3|^2)/2)
    # as before, except now k1,k2 are 3d vectors, not 2d.
    #
    # zeta(r1,r2) = (1/2pi)^4 int(d^2k1 int(d^2k2 exp(ik1.x1) exp(ik2.x2) B(k1,k2) ))
    #             = exp(-(x1^2 + y1^2 + x2^2 + y2^2 - x1x2 - y1y2)/3s^2) / 12 pi^2 s^4
    #             = exp(-(d1^2 + d2^2 + d3^2)/6s^2) / 24 sqrt(3) pi^3 s^6
    #
    # And again, this is also derivable as:
    # zeta(r1,r2) = int(dx int(dy int(dz n(x,y,z) n(x+x1,y+y1,z+z1) n(x+x2,y+y2,z+z2)))
    # which is also analytically integrable and gives the same answer.
    #
    # However, we need to correct for the uniform density background, so the real result
    # is this minus 1/L^6 divided by 1/L^6.  So:
    #
    # zeta(r1,r2) = 1/(24 sqrt(3) pi^3) (L/s)^4 exp(-(d1^2+d2^2+d3^2)/6s^2) - 1

    # Doing the full correlation function takes a long time.  Here, we just test a small range
    # of separations and a moderate range for u, v, which gives us a variety of triangle lengths.
    xcen = 823  # Mpc maybe?
    ycen = 342
    zcen = -672
    s = 10.
    if __name__ == "__main__":
        ngal = 5000
        nrand = 20 * ngal
        L = 50. * s
        tol_factor = 1
    else:
        ngal = 1000
        nrand = 5 * ngal
        L = 20. * s
        tol_factor = 5
    rng = np.random.RandomState(8675309)
    x = rng.normal(xcen, s, (ngal,) )
    y = rng.normal(ycen, s, (ngal,) )
    z = rng.normal(zcen, s, (ngal,) )

    r = np.sqrt(x*x+y*y+z*z)
    dec = np.arcsin(z/r) * (coord.radians / coord.degrees)
    ra = np.arctan2(y,x) * (coord.radians / coord.degrees)

    min_sep = 10.
    max_sep = 20.
    nbins = 8
    min_u = 0.9
    max_u = 1.0
    nubins = 1
    min_v = 0.
    max_v = 0.05
    nvbins = 1

    cat = treecorr.Catalog(ra=ra, dec=dec, r=r, ra_units='deg', dec_units='deg')
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins, verbose=1)
    ddd.process(cat)

    rx = (rng.random_sample(nrand)-0.5) * L + xcen
    ry = (rng.random_sample(nrand)-0.5) * L + ycen
    rz = (rng.random_sample(nrand)-0.5) * L + zcen
    rr = np.sqrt(rx*rx+ry*ry+rz*rz)
    rdec = np.arcsin(rz/rr) * (coord.radians / coord.degrees)
    rra = np.arctan2(ry,rx) * (coord.radians / coord.degrees)

    rand = treecorr.Catalog(ra=rra, dec=rdec, r=rr, ra_units='deg', dec_units='deg')
    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins, verbose=1)
    rrr.process(rand)

    d1 = ddd.meand1
    d2 = ddd.meand2
    d3 = ddd.meand3
    true_zeta = ((1./(24.*np.sqrt(3)*np.pi**3)) * (L/s)**6 *
                 np.exp(-(d1**2+d2**2+d3**2)/(6.*s**2)) - 1.)

    zeta, varzeta = ddd.calculateZeta(rrr=rrr)
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)),
                                  atol=0.1*tol_factor)

    # Check that we get the same result using the corr3 functin:
    cat.write(os.path.join('data','nnn_3d_data.dat'))
    rand.write(os.path.join('data','nnn_3d_rand.dat'))
    config = treecorr.config.read_config('configs/nnn_3d.yaml')
    config['verbose'] = 0
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_3d.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

    # Check that we get the same thing when using x,y,z rather than ra,dec,r
    cat = treecorr.Catalog(x=x, y=y, z=z)
    rand = treecorr.Catalog(x=rx, y=ry, z=rz)
    ddd.process(cat)
    rrr.process(rand)
    zeta, varzeta = ddd.calculateZeta(rrr=rrr)
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)),
                                  atol=0.1*tol_factor)


@timer
def test_list_logruv():
    # Test that we can use a list of files for either data or rand or both.
    data_cats = []
    rand_cats = []

    ncats = 3
    ngal = 100
    nrand = 2 * ngal
    s = 10.
    L = 50. * s
    rng = np.random.RandomState(8675309)

    min_sep = 30.
    max_sep = 50.
    nbins = 3
    min_u = 0
    max_u = 0.2
    nubins = 2
    min_v = 0.5
    max_v = 0.9
    nvbins = 2

    x = rng.normal(0,s, (ngal,ncats) )
    y = rng.normal(0,s, (ngal,ncats) )
    data_cats = [ treecorr.Catalog(x=x[:,k], y=y[:,k]) for k in range(ncats) ]
    rx = (rng.random_sample((nrand,ncats))-0.5) * L
    ry = (rng.random_sample((nrand,ncats))-0.5) * L
    rand_cats = [ treecorr.Catalog(x=rx[:,k], y=ry[:,k]) for k in range(ncats) ]

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins, bin_slop=0.1, verbose=1)
    ddd.process(data_cats)

    # Now do the same thing with one big catalog
    dddx = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                   nubins=nubins, nvbins=nvbins, bin_slop=0.1, verbose=1)
    data_catx = treecorr.Catalog(x=x.reshape( (ngal*ncats,) ), y=y.reshape( (ngal*ncats,) ))
    dddx.process(data_catx)
    # Only test to rtol=0.1, since there are now differences between the auto and cross related
    # to how they characterize triangles especially when d1 ~= d2 or d2 ~= d3.
    np.testing.assert_allclose(ddd.ntri, dddx.ntri, rtol=0.1)
    np.testing.assert_allclose(ddd.tot, dddx.tot)

    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins, bin_slop=0.1, verbose=1)
    rrr.process(rand_cats)

    rrrx = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                   nubins=nubins, nvbins=nvbins, bin_slop=0.1, verbose=1)
    rand_catx = treecorr.Catalog(x=rx.reshape( (nrand*ncats,) ), y=ry.reshape( (nrand*ncats,) ))
    rrrx.process(rand_catx)
    np.testing.assert_allclose(rrr.ntri, rrrx.ntri, rtol=0.1)
    np.testing.assert_allclose(rrr.tot, rrrx.tot)

    zeta, varzeta = ddd.calculateZeta(rrr=rrr)
    zetax, varzetax = dddx.calculateZeta(rrr=rrrx)
    np.testing.assert_allclose(zeta, zetax, rtol=0.1)

    # Check that we get the same result using the corr3 function:
    file_list = []
    rand_file_list = []
    for k in range(ncats):
        file_name = os.path.join('data','nnn_list_data%d.dat'%k)
        data_cats[k].write(file_name)
        file_list.append(file_name)

        rand_file_name = os.path.join('data','nnn_list_rand%d.dat'%k)
        rand_cats[k].write(rand_file_name)
        rand_file_list.append(rand_file_name)

    list_name = os.path.join('data','nnn_list_data_files.txt')
    with open(list_name, 'w') as fid:
        for file_name in file_list:
            fid.write('%s\n'%file_name)
    rand_list_name = os.path.join('data','nnn_list_rand_files.txt')
    with open(rand_list_name, 'w') as fid:
        for file_name in rand_file_list:
            fid.write('%s\n'%file_name)

    file_namex = os.path.join('data','nnn_list_datax.dat')
    data_catx.write(file_namex)

    rand_file_namex = os.path.join('data','nnn_list_randx.dat')
    rand_catx.write(rand_file_namex)

    config = treecorr.config.read_config('configs/nnn_list1.yaml')
    config['verbose'] = 0
    config['bin_slop'] = 0.1
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_list1.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

    config = treecorr.config.read_config('configs/nnn_list2.json')
    config['verbose'] = 0
    config['bin_slop'] = 0.1
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_list2.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=0.05)

    config = treecorr.config.read_config('configs/nnn_list3.params')
    config['verbose'] = 0
    config['bin_slop'] = 0.1
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_list3.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=0.05)

    config = treecorr.config.read_config('configs/nnn_list4.config', file_type='params')
    config['verbose'] = 0
    config['bin_slop'] = 0.1
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_list4.out'), names=True, skip_header=1)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

@timer
def test_direct_logsas_auto():
    # If the catalogs are small enough, we can do a direct count of the number of triangles
    # to see if comes out right.  This should exactly match the treecorr code if bin_slop=0.

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    cat = treecorr.Catalog(x=x, y=y)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_phi = 0.33
    max_phi = 2.89
    nphi_bins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  brute=True, verbose=1, bin_type='LogSAS')
    ddd.process(cat)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri = np.zeros( (nbins, nphi_bins, nbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = (max_phi-min_phi) / nphi_bins
    for i in range(ngal):
        for j in range(ngal):
            if i == j: continue
            for k in range(ngal):
                if i == k: continue
                if j == k: continue
                # i is the vertex where phi is (aka c1)
                # ik is d2, ij is d3.
                d1 = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2)
                d2 = np.sqrt((x[i]-x[k])**2 + (y[i]-y[k])**2)
                d3 = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2)
                if d1 == 0.: continue
                if d2 == 0.: continue
                if d3 == 0.: continue
                phi = np.arccos((d2**2 + d3**2 - d1**2)/(2*d2*d3))
                if not is_ccw(x[i],y[i],x[k],y[k],x[j],y[j]):
                    phi = 2*np.pi - phi
                if d2 < min_sep or d2 >= max_sep: continue
                if d3 < min_sep or d3 >= max_sep: continue
                if phi < min_phi or phi >= max_phi: continue
                kr2 = int(np.floor( (np.log(d2)-log_min_sep) / bin_size ))
                kr3 = int(np.floor( (np.log(d3)-log_min_sep) / bin_size ))
                kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                assert 0 <= kr2 < nbins
                assert 0 <= kphi < nphi_bins
                assert 0 <= kr3 < nbins
                true_ntri[kr2,kphi,kr3] += 1

    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Check that running via the corr3 script works correctly.
    file_name = os.path.join('data','nnn_direct_data_logsas.dat')
    with open(file_name, 'w') as fid:
        for i in range(ngal):
            fid.write(('%.20f %.20f\n')%(x[i],y[i]))
    L = 10*s
    nrand = ngal
    rx = (rng.random_sample(nrand)-0.5) * L
    ry = (rng.random_sample(nrand)-0.5) * L
    rcat = treecorr.Catalog(x=rx, y=ry)
    rand_file_name = os.path.join('data','nnn_direct_rand_logsas.dat')
    with open(rand_file_name, 'w') as fid:
        for i in range(nrand):
            fid.write(('%.20f %.20f\n')%(rx[i],ry[i]))
    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  brute=True, verbose=0, bin_type='LogSAS', rng=rng)
    rrr.process(rcat)
    zeta, varzeta = ddd.calculateZeta(rrr=rrr)

    config = treecorr.config.read_config('configs/nnn_direct_logsas.yaml')
    logger = treecorr.config.setup_logger(0)
    treecorr.corr3(config, logger)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_direct_logsas.out'), names=True,
                                    skip_header=1)
    np.testing.assert_allclose(corr3_output['d2_nom'], ddd.d2nom.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['d3_nom'], ddd.d3nom.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['phi_nom'], ddd.phi.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['DDD'], ddd.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['ntri'], ddd.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['RRR'], rrr.ntri.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)
    np.testing.assert_allclose(corr3_output['sigma_zeta'], np.sqrt(varzeta).flatten(), rtol=1.e-3)

    # Repeat with binslop = 0, since the code flow is different from brute=True
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, bin_type='LogSAS')
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, max_top=0, bin_type='LogSAS')
    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # And compare to the cross correlation
    # As before, this will count each triangle 6 times.
    ddd.process(cat,cat,cat)
    np.testing.assert_array_equal(ddd.ntri, 6*true_ntri)

    # But with ordered=True, it only counts each triangle once.
    ddd.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    # Or with 2 argument version, finds each triangle 3 times.
    ddd.process(cat,cat)
    np.testing.assert_array_equal(ddd.ntri, 3*true_ntri)

    ddd.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    do_pickle(ddd)

    # Split into patches to test the list-based version of the code.
    cat = treecorr.Catalog(x=x, y=y, npatch=10)

    ddd.process(cat)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)

    ddd.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    ddd.process(cat,cat, ordered=False)
    np.testing.assert_array_equal(ddd.ntri, 3*true_ntri)

    ddd.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(ddd.ntri, true_ntri)
    ddd.process(cat,cat,cat, ordered=False)
    np.testing.assert_array_equal(ddd.ntri, 6*true_ntri)

    # Test I/O
    ascii_name = 'output/nnn_ascii_logsas.txt'
    ddd.write(ascii_name, precision=16)
    ddd3 = treecorr.NNNCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nbins,
                                   nphi_bins=nphi_bins, bin_type='LogSAS')
    ddd3.read(ascii_name)
    np.testing.assert_allclose(ddd3.ntri, ddd.ntri)
    np.testing.assert_allclose(ddd3.weight, ddd.weight)
    np.testing.assert_allclose(ddd3.meand1, ddd.meand1)
    np.testing.assert_allclose(ddd3.meand2, ddd.meand2)
    np.testing.assert_allclose(ddd3.meand3, ddd.meand3)
    np.testing.assert_allclose(ddd3.meanlogd1, ddd.meanlogd1)
    np.testing.assert_allclose(ddd3.meanlogd2, ddd.meanlogd2)
    np.testing.assert_allclose(ddd3.meanlogd3, ddd.meanlogd3)
    np.testing.assert_allclose(ddd3.meanphi, ddd.meanphi)

    try:
        import fitsio
    except ImportError:
        pass
    else:
        fits_name = 'output/nnn_fits_logsas.fits'
        ddd.write(fits_name)
        ddd4 = treecorr.NNNCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nbins,
                                       nphi_bins=nphi_bins, bin_type='LogSAS')
        ddd4.read(fits_name)
        np.testing.assert_allclose(ddd4.ntri, ddd.ntri)
        np.testing.assert_allclose(ddd4.weight, ddd.weight)
        np.testing.assert_allclose(ddd4.meand1, ddd.meand1)
        np.testing.assert_allclose(ddd4.meand2, ddd.meand2)
        np.testing.assert_allclose(ddd4.meand3, ddd.meand3)
        np.testing.assert_allclose(ddd4.meanlogd1, ddd.meanlogd1)
        np.testing.assert_allclose(ddd4.meanlogd2, ddd.meanlogd2)
        np.testing.assert_allclose(ddd4.meanlogd3, ddd.meanlogd3)
        np.testing.assert_allclose(ddd4.meanphi, ddd.meanphi)


@timer
def test_direct_logsas_cross():
    # If the catalogs are small enough, we can do a direct count of the number of triangles
    # to see if comes out right.  This should exactly match the treecorr code if brute=True

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    cat3 = treecorr.Catalog(x=x3, y=y3)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_phi = 0.33
    max_phi = 2.89
    nphi_bins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  brute=True, verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('brute: ',t1-t0)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_123 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_132 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_213 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_231 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_312 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_321 = np.zeros( (nbins, nphi_bins, nbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = (max_phi-min_phi) / nphi_bins
    t0 = time.time()
    for i in range(ngal):
        for j in range(ngal):
            for k in range(ngal):
                d1 = np.sqrt((x2[j]-x3[k])**2 + (y2[j]-y3[k])**2)
                d2 = np.sqrt((x1[i]-x3[k])**2 + (y1[i]-y3[k])**2)
                d3 = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2)
                if d1 == 0.: continue
                if d2 == 0.: continue
                if d3 == 0.: continue

                kr1 = int(np.floor( (np.log(d1)-log_min_sep) / bin_size ))
                kr2 = int(np.floor( (np.log(d2)-log_min_sep) / bin_size ))
                kr3 = int(np.floor( (np.log(d3)-log_min_sep) / bin_size ))

                if d2 >= min_sep and d2 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    # 123
                    phi = np.arccos((d2**2 + d3**2 - d1**2)/(2*d2*d3))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_123[kr2,kphi,kr3] += 1

                    phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_132[kr3,kphi,kr2] += 1

                if d1 >= min_sep and d1 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr3 < nbins
                    # 231
                    phi = np.arccos((d1**2 + d3**2 - d2**2)/(2*d1*d3))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_231[kr3,kphi,kr1] += 1

                    # 213
                    phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_213[kr1,kphi,kr3] += 1

                if d1 >= min_sep and d1 < max_sep and d2 >= min_sep and d2 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr2 < nbins
                    # 312
                    phi = np.arccos((d1**2 + d2**2 - d3**2)/(2*d1*d2))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_312[kr1,kphi,kr2] += 1

                    # 321
                    phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_321[kr2,kphi,kr1] += 1
    t1 = time.time()
    print('Python brute: ',t1-t0)

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = true_ntri_123 + true_ntri_132 + true_ntri_213 + true_ntri_231 +\
            true_ntri_312 + true_ntri_321
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    # With ordered=True we get just the ones in the given order.
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('brute ordered 123: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)
    t0 = time.time()
    ddd.process(cat1, cat3, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 132: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_132)
    t0 = time.time()
    ddd.process(cat2, cat1, cat3, ordered=True)
    t1 = time.time()
    print('brute ordered 213: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_213)
    t0 = time.time()
    ddd.process(cat2, cat3, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 231: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_231)
    t0 = time.time()
    ddd.process(cat3, cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 312: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_312)
    t0 = time.time()
    ddd.process(cat3, cat2, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 321: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_321)

    # Repeat with binslop = 0
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('bin_slop=0 unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, max_top=0, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('no top unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('no top ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)

    # Split into patches to test the list-based version of the code.
    cat1 = treecorr.Catalog(x=x1, y=y1, npatch=10)
    cat2 = treecorr.Catalog(x=x2, y=y2, npatch=10)
    cat3 = treecorr.Catalog(x=x3, y=y3, npatch=10)

    # back to default top levels
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2, cat3)
    t1 = time.time()
    print('patch unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, cat3, ordered=True)
    t1 = time.time()
    print('patch ordered 123: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_123)
    t0 = time.time()
    ddd.process(cat1, cat3, cat2, ordered=True)
    t1 = time.time()
    print('patch ordered 132: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_132)
    t0 = time.time()
    ddd.process(cat2, cat1, cat3, ordered=True)
    t1 = time.time()
    print('patch ordered 213: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_213)
    t0 = time.time()
    ddd.process(cat2, cat3, cat1, ordered=True)
    t1 = time.time()
    print('patch ordered 231: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_231)
    t0 = time.time()
    ddd.process(cat3, cat1, cat2, ordered=True)
    t1 = time.time()
    print('patch ordered 312: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_312)
    t0 = time.time()
    ddd.process(cat3, cat2, cat1, ordered=True)
    t1 = time.time()
    print('patch ordered 321: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_321)


@timer
def test_direct_logsas_cross12():
    # Check the 1-2 cross correlation

    if __name__ == '__main__':
        ngal = 200
    else:
        ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2)

    min_sep = 1.
    max_sep = 50.
    nbins = 20
    min_phi = 0.33
    max_phi = 2.89
    nphi_bins = 10

    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  brute=True, verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('brute: ',t1-t0)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    true_ntri_122 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_212 = np.zeros( (nbins, nphi_bins, nbins) )
    true_ntri_221 = np.zeros( (nbins, nphi_bins, nbins) )
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = (max_phi-min_phi) / nphi_bins
    t0 = time.time()
    for i in range(ngal):
        for j in range(ngal):
            for k in range(ngal):
                if j == k: continue
                d1 = np.sqrt((x2[j]-x2[k])**2 + (y2[j]-y2[k])**2)
                d2 = np.sqrt((x1[i]-x2[k])**2 + (y1[i]-y2[k])**2)
                d3 = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2)
                if d1 == 0.: continue
                if d2 == 0.: continue
                if d3 == 0.: continue

                kr1 = int(np.floor( (np.log(d1)-log_min_sep) / bin_size ))
                kr2 = int(np.floor( (np.log(d2)-log_min_sep) / bin_size ))
                kr3 = int(np.floor( (np.log(d3)-log_min_sep) / bin_size ))

                # 123
                if d2 >= min_sep and d2 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    phi = np.arccos((d2**2 + d3**2 - d1**2)/(2*d2*d3))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_122[kr2,kphi,kr3] += 1

                # 231
                if d1 >= min_sep and d1 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr3 < nbins
                    phi = np.arccos((d1**2 + d3**2 - d2**2)/(2*d1*d3))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_221[kr3,kphi,kr1] += 1

                # 312
                if d1 >= min_sep and d1 < max_sep and d2 >= min_sep and d2 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr2 < nbins
                    phi = np.arccos((d1**2 + d2**2 - d3**2)/(2*d1*d2))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= min_phi and phi < max_phi:
                        kphi = int(np.floor( (phi-min_phi) / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_212[kr1,kphi,kr2] += 1
    t1 = time.time()
    print('Python brute: ',t1-t0)

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = true_ntri_122 + true_ntri_212 + true_ntri_221
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)

    # With ordered=True we get just the ones in the given order.
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('brute ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('brute ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

    # Repeat with binslop = 0
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('bin_slop=0 unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('bin_slop=0 ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

    # And again with no top-level recursion
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  bin_slop=0, verbose=1, max_top=0, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('no top unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('no top ordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('no top ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('no top ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

    # Split into patches to test the list-based version of the code.
    cat1 = treecorr.Catalog(x=x1, y=y1, npatch=10)
    cat2 = treecorr.Catalog(x=x2, y=y2, npatch=10)

    t0 = time.time()
    ddd.process(cat1, cat2)
    t1 = time.time()
    print('patch unordered: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_sum)
    t0 = time.time()
    ddd.process(cat1, cat2, ordered=True)
    t1 = time.time()
    print('patch ordered 122: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_122)
    t0 = time.time()
    ddd.process(cat2, cat1, cat2, ordered=True)
    t1 = time.time()
    print('patch ordered 212: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_212)
    t0 = time.time()
    ddd.process(cat2, cat2, cat1, ordered=True)
    t1 = time.time()
    print('patch ordered 221: ',t1-t0)
    np.testing.assert_array_equal(ddd.ntri, true_ntri_221)

@timer
def test_nnn_logsas():
    # Use a simple probability distribution for the galaxies:
    #
    # n(r) = (2pi s^2)^-1 exp(-r^2/2s^2)
    #
    # The Fourier transform is: n~(k) = exp(-s^2 k^2/2)
    # B(k1,k2) = <n~(k1) n~(k2) n~(-k1-k2)>
    #          = exp(-s^2 (|k1|^2 + |k2|^2 - k1.k2))
    #          = exp(-s^2 (|k1|^2 + |k2|^2 + |k3|^2)/2)
    #
    # zeta(r1,r2) = (1/2pi)^4 int(d^2k1 int(d^2k2 exp(ik1.x1) exp(ik2.x2) B(k1,k2) ))
    #             = exp(-(x1^2 + y1^2 + x2^2 + y2^2 - x1x2 - y1y2)/3s^2) / 12 pi^2 s^4
    #             = exp(-(d1^2 + d2^2 + d3^2)/6s^2) / 12 pi^2 s^4
    #
    # This is also derivable as:
    # zeta(r1,r2) = int(dx int(dy n(x,y) n(x+x1,y+y1) n(x+x2,y+y2)))
    # which is also analytically integrable and gives the same answer.
    #
    # However, we need to correct for the uniform density background, so the real result
    # is this minus 1/L^4 divided by 1/L^4.  So:
    #
    # zeta(r1,r2) = 1/(12 pi^2) (L/s)^4 exp(-(d1^2+d2^2+d3^2)/6s^2) - 1

    # Doing the full correlation function takes a long time.  Here, we just test a small range
    # of separations and a moderate range for u, v, which gives us a variety of triangle lengths.
    s = 10.
    if __name__ == "__main__":
        ngal = 20000
        nrand = 3 * ngal
        L = 50. * s  # Not infinity, so this introduces some error.  Our integrals were to infinity.
        tol_factor = 1
    else:
        ngal = 2000
        nrand = ngal
        L = 20. * s
        tol_factor = 5
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    min_sep = 11.
    max_sep = 13.
    nbins = 2
    min_phi = 0.8
    max_phi = 2.3
    nphi_bins = 15

    cat = treecorr.Catalog(x=x, y=y, x_units='arcmin', y_units='arcmin')
    ddd = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  sep_units='arcmin', verbose=1, bin_type='LogSAS')
    t0 = time.time()
    ddd.process(cat)
    t1 = time.time()
    print('auto process time = ',t1-t0)

    # Doing 3 catalogs ordered, should be equivalent.  Not numerically identical, but
    # basically the same answer.
    dddc = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                   sep_units='arcmin', verbose=1, bin_type='LogSAS')
    t0 = time.time()
    dddc.process(cat,cat,cat, ordered=True)
    t1 = time.time()
    print('cross process time = ',t1-t0)
    np.testing.assert_allclose(dddc.ntri, ddd.ntri)
    np.testing.assert_allclose(dddc.meanlogd1, ddd.meanlogd1)
    np.testing.assert_allclose(dddc.meanlogd2, ddd.meanlogd2)
    np.testing.assert_allclose(dddc.meanlogd3, ddd.meanlogd3)
    np.testing.assert_allclose(dddc.meanphi, ddd.meanphi)

    t0 = time.time()
    dddc.process(cat,cat, ordered=True)
    t1 = time.time()
    print('cross12 process time = ',t1-t0)
    np.testing.assert_allclose(dddc.ntri, ddd.ntri)
    np.testing.assert_allclose(dddc.meanlogd1, ddd.meanlogd1)
    np.testing.assert_allclose(dddc.meanlogd2, ddd.meanlogd2)
    np.testing.assert_allclose(dddc.meanlogd3, ddd.meanlogd3)
    np.testing.assert_allclose(dddc.meanphi, ddd.meanphi)

    # log(<d>) != <logd>, but it should be close:
    print('meanlogd1 - log(meand1) = ',ddd.meanlogd1 - np.log(ddd.meand1))
    print('meanlogd2 - log(meand2) = ',ddd.meanlogd2 - np.log(ddd.meand2))
    print('meanlogd3 - log(meand3) = ',ddd.meanlogd3 - np.log(ddd.meand3))
    np.testing.assert_allclose(ddd.meanlogd1, np.log(ddd.meand1), rtol=1.e-3)
    np.testing.assert_allclose(ddd.meanlogd2, np.log(ddd.meand2), rtol=1.e-3)
    np.testing.assert_allclose(ddd.meanlogd3, np.log(ddd.meand3), rtol=1.e-3)

    rx = (rng.random_sample(nrand)-0.5) * L
    ry = (rng.random_sample(nrand)-0.5) * L
    rand = treecorr.Catalog(x=rx,y=ry, x_units='arcmin', y_units='arcmin')
    rrr = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  sep_units='arcmin', verbose=1, bin_type='LogSAS')
    rrr.process(rand)

    d1 = ddd.meand1
    d2 = ddd.meand2
    d3 = ddd.meand3
    phi = ddd.meanphi
    true_zeta = (1./(12.*np.pi**2)) * (L/s)**4 * np.exp(-(d1**2+d2**2+d3**2)/(6.*s**2)) - 1.

    zeta, varzeta = ddd.calculateZeta(rrr=rrr)
    print('zeta = ',zeta)
    print('true_zeta = ',true_zeta)
    print('ratio = ',zeta / true_zeta)
    print('diff = ',zeta - true_zeta)
    print('max rel diff = ',np.max(np.abs((zeta - true_zeta)/true_zeta)))
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)),
                                  atol=0.1*tol_factor)

    # Check that we get the same result using the corr3 function
    cat.write(os.path.join('data','nnn_data_logsas.dat'))
    rand.write(os.path.join('data','nnn_rand_logsas.dat'))
    config = treecorr.config.read_config('configs/nnn_logsas.yaml')
    config['verbose'] = 3
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','nnn_logsas.out'), names=True, skip_header=1)
    print('zeta = ',zeta)
    print('from corr3 output = ',corr3_output['zeta'])
    print('ratio = ',corr3_output['zeta']/zeta.flatten())
    print('diff = ',corr3_output['zeta']-zeta.flatten())
    np.testing.assert_allclose(corr3_output['zeta'], zeta.flatten(), rtol=1.e-3)

    # Check the fits write option
    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name1 = os.path.join('output','nnn_out1_logsas.fits')
        ddd.write(out_file_name1)
        data = fitsio.read(out_file_name1)
        np.testing.assert_almost_equal(data['d2_nom'], np.exp(ddd.logd2).flatten())
        np.testing.assert_almost_equal(data['d3_nom'], np.exp(ddd.logd3).flatten())
        np.testing.assert_almost_equal(data['phi_nom'], ddd.phi.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanphi'], ddd.meanphi.flatten())
        np.testing.assert_almost_equal(data['ntri'], ddd.ntri.flatten())
        header = fitsio.read_header(out_file_name1, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        out_file_name2 = os.path.join('output','nnn_out2_logsas.fits')
        ddd.write(out_file_name2, rrr=rrr)
        data = fitsio.read(out_file_name2)
        np.testing.assert_almost_equal(data['d2_nom'], np.exp(ddd.logd2).flatten())
        np.testing.assert_almost_equal(data['d3_nom'], np.exp(ddd.logd3).flatten())
        np.testing.assert_almost_equal(data['phi_nom'], ddd.phi.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanphi'], ddd.meanphi.flatten())
        np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        header = fitsio.read_header(out_file_name2, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        # Check the read function
        # Note: These don't need the flatten.
        # The read function should reshape them to the right shape.
        ddd2 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                       sep_units='arcmin', verbose=1, bin_type='LogSAS')
        ddd2.read(out_file_name1)
        np.testing.assert_almost_equal(ddd2.logd2, ddd.logd2)
        np.testing.assert_almost_equal(ddd2.logd3, ddd.logd3)
        np.testing.assert_almost_equal(ddd2.phi, ddd.phi)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanphi, ddd.meanphi)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

        ddd2.read(out_file_name2)
        np.testing.assert_almost_equal(ddd2.logd2, ddd.logd2)
        np.testing.assert_almost_equal(ddd2.logd3, ddd.logd3)
        np.testing.assert_almost_equal(ddd2.phi, ddd.phi)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanphi, ddd.meanphi)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

    # Check the hdf5 write option
    try:
        import h5py  # noqa: F401
    except ImportError:
        pass
    else:
        out_file_name3 = os.path.join('output','nnn_out3_logsas.hdf5')
        ddd.write(out_file_name3, rrr=rrr)
        with h5py.File(out_file_name3, 'r') as hdf:
            data = hdf['/']
            np.testing.assert_almost_equal(data['d2_nom'], np.exp(ddd.logd2).flatten())
            np.testing.assert_almost_equal(data['d3_nom'], np.exp(ddd.logd3).flatten())
            np.testing.assert_almost_equal(data['phi_nom'], ddd.phi.flatten())
            np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
            np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
            np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
            np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
            np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
            np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
            np.testing.assert_almost_equal(data['meanphi'], ddd.meanphi.flatten())
            np.testing.assert_almost_equal(data['ntri'], ddd.ntri.flatten())
            np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
            np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
            np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
            np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
            attrs = data.attrs
            np.testing.assert_almost_equal(attrs['tot']/ddd.tot, 1.)

        ddd3 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                       sep_units='arcmin', verbose=1, bin_type='LogSAS')
        ddd3.read(out_file_name3)
        np.testing.assert_almost_equal(ddd3.logd2, ddd.logd2)
        np.testing.assert_almost_equal(ddd3.logd3, ddd.logd3)
        np.testing.assert_almost_equal(ddd3.phi, ddd.phi)
        np.testing.assert_almost_equal(ddd3.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd3.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd3.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd3.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd3.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd3.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd3.meanphi, ddd.meanphi)
        np.testing.assert_almost_equal(ddd3.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd3.tot/ddd.tot, 1.)
        assert ddd3.coords == ddd.coords
        assert ddd3.metric == ddd.metric
        assert ddd3.sep_units == ddd.sep_units
        assert ddd3.bin_type == ddd.bin_type

    # Test compensated zeta
    # First just check the mechanics.
    # If we don't actually do all the cross terms, then compensated is the same as simple.
    zeta2, varzeta2 = ddd.calculateZeta(rrr=rrr, drr=rrr, rdd=rrr)
    print('fake compensated zeta = ',zeta2)
    np.testing.assert_allclose(zeta2, zeta)

    # Error to not have one of rrr, drr, rdd.
    with assert_raises(TypeError):
        ddd.calculateZeta(drr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.calculateZeta(rrr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.calculateZeta(rrr=rrr, drr=rrr)
    rrr2 = treecorr.NNNCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                   sep_units='arcmin', bin_type='LogSAS')
    # Error if any of them haven't been run yet.
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr2, drr=rrr, rdd=rrr)
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr, drr=rrr2, rdd=rrr)
    with assert_raises(ValueError):
        ddd.calculateZeta(rrr=rrr, drr=rrr, rdd=rrr2)

    out_file_name3 = os.path.join('output','nnn_out3_logsas.dat')
    with assert_raises(TypeError):
        ddd.write(out_file_name3, drr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.write(out_file_name3, rrr=rrr, rdd=rrr)
    with assert_raises(TypeError):
        ddd.write(out_file_name3, rrr=rrr, drr=rrr)

    # This version computes the three-point function after subtracting off the appropriate
    # two-point functions xi(d1) + xi(d2) + xi(d3), where [cf. test_nn() in test_nn.py]
    # xi(r) = 1/4pi (L/s)^2 exp(-r^2/4s^2) - 1
    drr = ddd.copy()
    rdd = ddd.copy()

    drr.process(cat,rand)
    rdd.process(rand,cat)

    zeta, varzeta = ddd.calculateZeta(rrr=rrr, drr=drr, rdd=rdd)
    print('compensated zeta = ',zeta)

    xi1 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d1**2/(4.*s**2)) - 1.
    xi2 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d2**2/(4.*s**2)) - 1.
    xi3 = (1./(4.*np.pi)) * (L/s)**2 * np.exp(-d3**2/(4.*s**2)) - 1.
    print('xi1 = ',xi1)
    print('xi2 = ',xi2)
    print('xi3 = ',xi3)
    print('true_zeta + xi1 + xi2 + xi3 = ',true_zeta)
    true_zeta -= xi1 + xi2 + xi3
    print('true_zeta => ',true_zeta)
    print('ratio = ',zeta / true_zeta)
    print('diff = ',zeta - true_zeta)
    print('max rel diff = ',np.max(np.abs((zeta - true_zeta)/true_zeta)))
    np.testing.assert_allclose(zeta, true_zeta, rtol=0.1*tol_factor)
    np.testing.assert_allclose(np.log(np.abs(zeta)), np.log(np.abs(true_zeta)), atol=0.1*tol_factor)

    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name3 = os.path.join('output','nnn_out3_logsas.fits')
        ddd.write(out_file_name3, rrr=rrr, drr=drr, rdd=rdd)
        data = fitsio.read(out_file_name3)
        np.testing.assert_almost_equal(data['d2_nom'], np.exp(ddd.logd2).flatten())
        np.testing.assert_almost_equal(data['d3_nom'], np.exp(ddd.logd3).flatten())
        np.testing.assert_almost_equal(data['phi_nom'], ddd.phi.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanphi'], ddd.meanphi.flatten())
        np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        np.testing.assert_almost_equal(data['DRR'], drr.ntri.flatten() * (ddd.tot / drr.tot))
        np.testing.assert_almost_equal(data['RDD'], rdd.ntri.flatten() * (ddd.tot / rdd.tot))
        header = fitsio.read_header(out_file_name3, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)

        ddd2.read(out_file_name3)
        np.testing.assert_almost_equal(ddd2.logd2, ddd.logd2)
        np.testing.assert_almost_equal(ddd2.logd3, ddd.logd3)
        np.testing.assert_almost_equal(ddd2.phi, ddd.phi)
        np.testing.assert_almost_equal(ddd2.meand1, ddd.meand1)
        np.testing.assert_almost_equal(ddd2.meanlogd1, ddd.meanlogd1)
        np.testing.assert_almost_equal(ddd2.meand2, ddd.meand2)
        np.testing.assert_almost_equal(ddd2.meanlogd2, ddd.meanlogd2)
        np.testing.assert_almost_equal(ddd2.meand3, ddd.meand3)
        np.testing.assert_almost_equal(ddd2.meanlogd3, ddd.meanlogd3)
        np.testing.assert_almost_equal(ddd2.meanphi, ddd.meanphi)
        np.testing.assert_almost_equal(ddd2.ntri, ddd.ntri)
        np.testing.assert_almost_equal(ddd2.tot/ddd.tot, 1.)
        assert ddd2.coords == ddd.coords
        assert ddd2.metric == ddd.metric
        assert ddd2.sep_units == ddd.sep_units
        assert ddd2.bin_type == ddd.bin_type

        config['nnn_statistic'] = 'compensated'
        config['verbose'] = 0
        treecorr.corr3(config)
        data = fitsio.read(out_file_name3)

        np.testing.assert_almost_equal(data['d2_nom'], np.exp(ddd.logd2).flatten())
        np.testing.assert_almost_equal(data['d3_nom'], np.exp(ddd.logd3).flatten())
        np.testing.assert_almost_equal(data['phi_nom'], ddd.phi.flatten())
        np.testing.assert_almost_equal(data['meand1'], ddd.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], ddd.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], ddd.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], ddd.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], ddd.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], ddd.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanphi'], ddd.meanphi.flatten())
        np.testing.assert_almost_equal(data['zeta'], zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(varzeta).flatten())
        np.testing.assert_almost_equal(data['DDD'], ddd.ntri.flatten())
        np.testing.assert_almost_equal(data['RRR'], rrr.ntri.flatten() * (ddd.tot / rrr.tot))
        np.testing.assert_almost_equal(data['DRR'], drr.ntri.flatten() * (ddd.tot / drr.tot))
        np.testing.assert_almost_equal(data['RDD'], rdd.ntri.flatten() * (ddd.tot / rdd.tot))
        header = fitsio.read_header(out_file_name3, 1)
        np.testing.assert_almost_equal(header['tot']/ddd.tot, 1.)



if __name__ == '__main__':
    test_logruv_binning()
    test_logsas_binning()
    test_direct_logruv_auto()
    test_direct_logruv_cross()
    test_direct_logruv_cross12()
    test_direct_logruv_spherical()
    test_direct_logruv_arc()
    test_direct_logruv_partial()
    test_direct_logruv_3d_auto()
    test_direct_logruv_3d_cross()
    test_nnn_logruv()
    test_3d_logruv()
    test_list_logruv()
    test_direct_logsas_auto()
    test_direct_logsas_cross()
    test_direct_logsas_cross12()
    test_nnn_logsas()
