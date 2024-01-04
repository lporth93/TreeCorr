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
import time

from test_helper import do_pickle, assert_raises, timer, is_ccw, is_ccw_3d

@timer
def test_direct_logruv():
    # If the catalogs are small enough, we can do a direct calculation to see if comes out right.
    # This should exactly match the treecorr result if brute=True.

    ngal = 100
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    w = rng.random_sample(ngal)
    kap = rng.normal(0,sig_kap, (ngal,) )

    cat = treecorr.Catalog(x=x, y=y, w=w, k=kap)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    nubins = 5
    nvbins = 5
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins, brute=True)
    kkk.process(cat, num_threads=2)

    true_ntri = np.zeros((nrbins, nubins, 2*nvbins), dtype=int)
    true_weight = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)
    true_zeta = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)
    for i in range(ngal):
        for j in range(i+1,ngal):
            for k in range(j+1,ngal):
                d12 = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2)
                d23 = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2)
                d31 = np.sqrt((x[k]-x[i])**2 + (y[k]-y[i])**2)

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
                if not is_ccw(x[ii],y[ii],x[jj],y[jj],x[kk],y[kk]):
                    v = -v

                uindex = np.floor(u / bin_size).astype(int)
                assert 0 <= uindex < nubins
                vindex = np.floor((v+1) / bin_size).astype(int)
                assert 0 <= vindex < 2*nvbins

                www = w[i] * w[j] * w[k]
                zeta = www * kap[i] * kap[j] * kap[k]

                true_ntri[rindex,uindex,vindex] += 1
                true_weight[rindex,uindex,vindex] += www
                true_zeta[rindex,uindex,vindex] += zeta

    pos = true_weight > 0
    true_zeta[pos] /= true_weight[pos]

    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/kkk_direct.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['kkk_file_name'])
        np.testing.assert_allclose(data['r_nom'], kkk.rnom.flatten())
        np.testing.assert_allclose(data['u_nom'], kkk.u.flatten())
        np.testing.assert_allclose(data['v_nom'], kkk.v.flatten())
        np.testing.assert_allclose(data['ntri'], kkk.ntri.flatten())
        np.testing.assert_allclose(data['weight'], kkk.weight.flatten())
        np.testing.assert_allclose(data['zeta'], kkk.zeta.flatten(), rtol=1.e-3)

    # Also check the cross calculation.
    # Here, we get 6x as many triangles, since each triangle is discovered 6 times.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins, brute=True)
    kkk.process(cat, cat, cat, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, 6*true_ntri)
    np.testing.assert_allclose(kkk.weight, 6*true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # But with ordered=True, it only counts each triangle once.
    kkk.process(cat,cat,cat, ordered=True, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Or with 2 argument version, finds each triangle 3 times.
    kkk.process(cat,cat)
    np.testing.assert_array_equal(kkk.ntri, 3*true_ntri)
    np.testing.assert_allclose(kkk.weight, 3*true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  bin_slop=0, max_top=0)
    kkk.process(cat)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Check a few basic operations with a KKKCorrelation object.
    do_pickle(kkk)

    kkk2 = kkk.copy()
    kkk2 += kkk
    np.testing.assert_allclose(kkk2.ntri, 2*kkk.ntri)
    np.testing.assert_allclose(kkk2.weight, 2*kkk.weight)
    np.testing.assert_allclose(kkk2.meand1, 2*kkk.meand1)
    np.testing.assert_allclose(kkk2.meand2, 2*kkk.meand2)
    np.testing.assert_allclose(kkk2.meand3, 2*kkk.meand3)
    np.testing.assert_allclose(kkk2.meanlogd1, 2*kkk.meanlogd1)
    np.testing.assert_allclose(kkk2.meanlogd2, 2*kkk.meanlogd2)
    np.testing.assert_allclose(kkk2.meanlogd3, 2*kkk.meanlogd3)
    np.testing.assert_allclose(kkk2.meanu, 2*kkk.meanu)
    np.testing.assert_allclose(kkk2.meanv, 2*kkk.meanv)
    np.testing.assert_allclose(kkk2.zeta, 2*kkk.zeta)

    kkk2.clear()
    kkk2 += kkk
    np.testing.assert_allclose(kkk2.ntri, kkk.ntri)
    np.testing.assert_allclose(kkk2.weight, kkk.weight)
    np.testing.assert_allclose(kkk2.meand1, kkk.meand1)
    np.testing.assert_allclose(kkk2.meand2, kkk.meand2)
    np.testing.assert_allclose(kkk2.meand3, kkk.meand3)
    np.testing.assert_allclose(kkk2.meanlogd1, kkk.meanlogd1)
    np.testing.assert_allclose(kkk2.meanlogd2, kkk.meanlogd2)
    np.testing.assert_allclose(kkk2.meanlogd3, kkk.meanlogd3)
    np.testing.assert_allclose(kkk2.meanu, kkk.meanu)
    np.testing.assert_allclose(kkk2.meanv, kkk.meanv)
    np.testing.assert_allclose(kkk2.zeta, kkk.zeta)

    ascii_name = 'output/kkk_ascii.txt'
    kkk.write(ascii_name, precision=16)
    kkk3 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins)
    kkk3.read(ascii_name)
    np.testing.assert_allclose(kkk3.ntri, kkk.ntri)
    np.testing.assert_allclose(kkk3.weight, kkk.weight)
    np.testing.assert_allclose(kkk3.meand1, kkk.meand1)
    np.testing.assert_allclose(kkk3.meand2, kkk.meand2)
    np.testing.assert_allclose(kkk3.meand3, kkk.meand3)
    np.testing.assert_allclose(kkk3.meanlogd1, kkk.meanlogd1)
    np.testing.assert_allclose(kkk3.meanlogd2, kkk.meanlogd2)
    np.testing.assert_allclose(kkk3.meanlogd3, kkk.meanlogd3)
    np.testing.assert_allclose(kkk3.meanu, kkk.meanu)
    np.testing.assert_allclose(kkk3.meanv, kkk.meanv)
    np.testing.assert_allclose(kkk3.zeta, kkk.zeta)

    try:
        import fitsio
    except ImportError:
        pass
    else:
        fits_name = 'output/kkk_fits.fits'
        kkk.write(fits_name)
        kkk4 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins)
        kkk4.read(fits_name)
        np.testing.assert_allclose(kkk4.ntri, kkk.ntri)
        np.testing.assert_allclose(kkk4.weight, kkk.weight)
        np.testing.assert_allclose(kkk4.meand1, kkk.meand1)
        np.testing.assert_allclose(kkk4.meand2, kkk.meand2)
        np.testing.assert_allclose(kkk4.meand3, kkk.meand3)
        np.testing.assert_allclose(kkk4.meanlogd1, kkk.meanlogd1)
        np.testing.assert_allclose(kkk4.meanlogd2, kkk.meanlogd2)
        np.testing.assert_allclose(kkk4.meanlogd3, kkk.meanlogd3)
        np.testing.assert_allclose(kkk4.meanu, kkk.meanu)
        np.testing.assert_allclose(kkk4.meanv, kkk.meanv)
        np.testing.assert_allclose(kkk4.zeta, kkk.zeta)

    with assert_raises(TypeError):
        kkk2 += config
    kkk5 = treecorr.KKKCorrelation(min_sep=min_sep/2, bin_size=bin_size, nbins=nrbins)
    with assert_raises(ValueError):
        kkk2 += kkk5
    kkk6 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size/2, nbins=nrbins)
    with assert_raises(ValueError):
        kkk2 += kkk6
    kkk7 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins*2)
    with assert_raises(ValueError):
        kkk2 += kkk7
    kkk8 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   min_u=0.1)
    with assert_raises(ValueError):
        kkk2 += kkk8
    kkk0 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   max_u=0.1)
    with assert_raises(ValueError):
        kkk2 += kkk0
    kkk10 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   nubins=nrbins*2)
    with assert_raises(ValueError):
        kkk2 += kkk10
    kkk11 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   min_v=0.1)
    with assert_raises(ValueError):
        kkk2 += kkk11
    kkk12 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   max_v=0.1)
    with assert_raises(ValueError):
        kkk2 += kkk12
    kkk13 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                   nvbins=nrbins*2)
    with assert_raises(ValueError):
        kkk2 += kkk13


@timer
def test_direct_logruv_spherical():
    # Repeat in spherical coords

    ngal = 50
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) ) + 200  # Put everything at large y, so small angle on sky
    z = rng.normal(0,s, (ngal,) )
    w = rng.random_sample(ngal)
    kap = rng.normal(0,3, (ngal,) )
    #w = np.ones_like(w)

    ra, dec = coord.CelestialCoord.xyz_to_radec(x,y,z)

    cat = treecorr.Catalog(ra=ra, dec=dec, ra_units='rad', dec_units='rad', w=w, k=kap)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    nubins = 5
    nvbins = 5
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  sep_units='deg', brute=True)
    kkk.process(cat)

    r = np.sqrt(x**2 + y**2 + z**2)
    x /= r;  y /= r;  z /= r

    true_ntri = np.zeros((nrbins, nubins, 2*nvbins), dtype=int)
    true_weight = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)
    true_zeta = np.zeros((nrbins, nubins, 2*nvbins), dtype=float)

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
                if not is_ccw_3d(x[ii],y[ii],z[ii],x[jj],y[jj],z[jj],x[kk],y[kk],z[kk]):
                    v = -v

                uindex = np.floor(u / bin_size).astype(int)
                assert 0 <= uindex < nubins
                vindex = np.floor((v+1) / bin_size).astype(int)
                assert 0 <= vindex < 2*nvbins

                www = w[i] * w[j] * w[k]
                zeta = www * kap[i] * kap[j] * kap[k]

                true_ntri[rindex,uindex,vindex] += 1
                true_weight[rindex,uindex,vindex] += www
                true_zeta[rindex,uindex,vindex] += zeta

    pos = true_weight > 0
    true_zeta[pos] /= true_weight[pos]

    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-4, atol=1.e-6)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/kkk_direct_spherical.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['kkk_file_name'])
        np.testing.assert_allclose(data['r_nom'], kkk.rnom.flatten())
        np.testing.assert_allclose(data['u_nom'], kkk.u.flatten())
        np.testing.assert_allclose(data['v_nom'], kkk.v.flatten())
        np.testing.assert_allclose(data['ntri'], kkk.ntri.flatten())
        np.testing.assert_allclose(data['weight'], kkk.weight.flatten())
        np.testing.assert_allclose(data['zeta'], kkk.zeta.flatten(), rtol=1.e-3)

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  sep_units='deg', bin_slop=0, max_top=0)
    kkk.process(cat)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-4, atol=1.e-6)

@timer
def test_direct_logruv_cross():
    # If the catalogs are small enough, we can do a direct calculation to see if comes out right.
    # This should exactly match the treecorr result if brute=True.

    ngal = 50
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    w1 = rng.random_sample(ngal)
    k1 = rng.normal(0,sig_kap, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    w2 = rng.random_sample(ngal)
    k2 = rng.normal(0,sig_kap, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    w3 = rng.random_sample(ngal)
    k3 = rng.normal(0,sig_kap, (ngal,) )
    cat3 = treecorr.Catalog(x=x3, y=y3, w=w3, k=k3)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    min_u = 0.13
    max_u = 0.89
    nubins = 5
    min_v = 0.13
    max_v = 0.59
    nvbins = 5

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True)
    kkk.process(cat1, cat2, cat3, num_threads=2)

    # Figure out the correct answer for each permutation
    true_ntri_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    max_sep = min_sep * np.exp(nrbins*bin_size)
    log_min_sep = np.log(min_sep)
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
                        true_zeta = true_zeta_123
                        true_weight = true_weight_123
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x1[i],y1[i],x3[k],y3[k])
                        true_ntri = true_ntri_213
                        true_zeta = true_zeta_213
                        true_weight = true_weight_213
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x3[k],y3[k],x1[i],y1[i])
                        true_ntri = true_ntri_231
                        true_zeta = true_zeta_231
                        true_weight = true_weight_231
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j])
                        true_ntri = true_ntri_132
                        true_zeta = true_zeta_132
                        true_weight = true_weight_132
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x1[i],y1[i],x2[j],y2[j])
                        true_ntri = true_ntri_312
                        true_zeta = true_zeta_312
                        true_weight = true_weight_312
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x3[k],y3[k],x2[j],y2[j],x1[i],y1[i])
                        true_ntri = true_ntri_321
                        true_zeta = true_zeta_321
                        true_weight = true_weight_321

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
                assert 0 <= kr < nrbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                www = w1[i] * w2[j] * w3[k]
                zeta = www * k1[i] * k2[j] * k3[k]
                true_ntri[kr,ku,kv] += 1
                true_weight[kr,ku,kv] += www
                true_zeta[kr,ku,kv] += zeta

    n_list = [true_ntri_123, true_ntri_132, true_ntri_213, true_ntri_231,
              true_ntri_312, true_ntri_321]
    w_list = [true_weight_123, true_weight_132, true_weight_213, true_weight_231,
              true_weight_312, true_weight_321]
    z_list = [true_zeta_123, true_zeta_132, true_zeta_213, true_zeta_231,
              true_zeta_312, true_zeta_321]

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = sum(n_list)
    true_weight_sum = sum(w_list)
    true_zeta_sum = sum(z_list)
    pos = true_weight_sum > 0
    true_zeta_sum[pos] /= true_weight_sum[pos]
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-5)

    # Now normalize each one individually.
    for w,z in zip(w_list, z_list):
        pos = w > 0
        z[pos] /= w[pos]

    # With ordered=True we get just the ones in the given order.
    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)
    kkk.process(cat1, cat3, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_132)
    np.testing.assert_allclose(kkk.weight, true_weight_132, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_132, rtol=1.e-5)
    kkk.process(cat2, cat1, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_213)
    np.testing.assert_allclose(kkk.weight, true_weight_213, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_213, rtol=1.e-5)
    kkk.process(cat2, cat3, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_231)
    np.testing.assert_allclose(kkk.weight, true_weight_231, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_231, rtol=1.e-5)
    kkk.process(cat3, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_312)
    np.testing.assert_allclose(kkk.weight, true_weight_312, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_312, rtol=1.e-5)
    kkk.process(cat3, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_321)
    np.testing.assert_allclose(kkk.weight, true_weight_321, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_321, rtol=1.e-5)

    # Repeat with binslop = 0
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)

    # And again with no top-level recursion
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)

    # Error to have cat3, but not cat2
    with assert_raises(ValueError):
        kkk.process(cat1, cat3=cat3)


@timer
def test_direct_logruv_cross12():
    # Check the 1-2 cross correlation

    ngal = 50
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    w1 = rng.random_sample(ngal)
    k1 = rng.normal(0,sig_kap, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    w2 = rng.random_sample(ngal)
    k2 = rng.normal(0,sig_kap, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    min_u = 0.13
    max_u = 0.89
    nubins = 5
    min_v = 0.13
    max_v = 0.59
    nvbins = 5

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True)
    kkk.process(cat1, cat2, num_threads=2)

    # Figure out the correct answer for each permutation
    true_ntri_122 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_212 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_221 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_122 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_212 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_221 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_122 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_212 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_221 = np.zeros( (nrbins, nubins, 2*nvbins) )
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    max_sep = min_sep * np.exp(nrbins*bin_size)
    log_min_sep = np.log(min_sep)
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
                        true_zeta = true_zeta_122
                        true_weight = true_weight_122
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x1[i],y1[i],x2[k],y2[k])
                        true_ntri = true_ntri_212
                        true_zeta = true_zeta_212
                        true_weight = true_weight_212
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw(x2[j],y2[j],x2[k],y2[k],x1[i],y1[i])
                        true_ntri = true_ntri_221
                        true_zeta = true_zeta_221
                        true_weight = true_weight_221
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j])
                        true_ntri = true_ntri_122
                        true_zeta = true_zeta_122
                        true_weight = true_weight_122
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw(x2[k],y2[k],x1[i],y1[i],x2[j],y2[j])
                        true_ntri = true_ntri_212
                        true_zeta = true_zeta_212
                        true_weight = true_weight_212
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw(x2[k],y2[k],x2[j],y2[j],x1[i],y1[i])
                        true_ntri = true_ntri_221
                        true_zeta = true_zeta_221
                        true_weight = true_weight_221

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
                assert 0 <= kr < nrbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                www = w1[i] * w2[j] * w2[k]
                zeta = www * k1[i] * k2[j] * k2[k]
                true_ntri[kr,ku,kv] += 1
                true_weight[kr,ku,kv] += www
                true_zeta[kr,ku,kv] += zeta

    n_list = [true_ntri_122, true_ntri_212, true_ntri_221]
    w_list = [true_weight_122, true_weight_212, true_weight_221]
    z_list = [true_zeta_122, true_zeta_212, true_zeta_221]

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = sum(n_list)
    true_weight_sum = sum(w_list)
    true_zeta_sum = sum(z_list)
    pos = true_weight_sum > 0
    true_zeta_sum[pos] /= true_weight_sum[pos]
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-5)

    # Now normalize each one individually.
    for w,z in zip(w_list, z_list):
        pos = w > 0
        z[pos] /= w[pos]

    # With ordered=True we get just the ones in the given order.
    kkk.process(cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_122)
    np.testing.assert_allclose(kkk.weight, true_weight_122, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_122, rtol=1.e-5)
    kkk.process(cat2, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_212)
    np.testing.assert_allclose(kkk.weight, true_weight_212, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_212, rtol=1.e-5)
    kkk.process(cat2, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_221)
    np.testing.assert_allclose(kkk.weight, true_weight_221, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_221, rtol=1.e-5)

    # Split into patches to test the list-based version of the code.
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1, npatch=4)
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2, npatch=4)

    kkk.process(cat1, cat2, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-5)

    kkk.process(cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_122)
    np.testing.assert_allclose(kkk.weight, true_weight_122, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_122, rtol=1.e-5)
    kkk.process(cat2, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_212)
    np.testing.assert_allclose(kkk.weight, true_weight_212, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_212, rtol=1.e-5)
    kkk.process(cat2, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_221)
    np.testing.assert_allclose(kkk.weight, true_weight_221, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_221, rtol=1.e-5)


@timer
def test_direct_logruv_cross_3d():
    # Now in 3d

    ngal = 50
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    z1 = rng.normal(0,s, (ngal,) )
    w1 = rng.random_sample(ngal)
    k1 = rng.normal(0,sig_kap, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1, z=z1, w=w1, k=k1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    z2 = rng.normal(0,s, (ngal,) )
    w2 = rng.random_sample(ngal)
    k2 = rng.normal(0,sig_kap, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2, z=z2, w=w2, k=k2)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    z3 = rng.normal(0,s, (ngal,) )
    w3 = rng.random_sample(ngal)
    k3 = rng.normal(0,sig_kap, (ngal,) )
    cat3 = treecorr.Catalog(x=x3, y=y3, z=z3, w=w3, k=k3)

    min_sep = 1.
    bin_size = 0.2
    nrbins = 10
    min_u = 0.13
    max_u = 0.89
    nubins = 5
    min_v = 0.13
    max_v = 0.59
    nvbins = 5

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  brute=True)
    kkk.process(cat1, cat2, cat3, num_threads=2)

    # Figure out the correct answer for each permutation
    true_ntri_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_ntri_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_zeta_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_123 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_132 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_213 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_231 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_312 = np.zeros( (nrbins, nubins, 2*nvbins) )
    true_weight_321 = np.zeros( (nrbins, nubins, 2*nvbins) )
    ubin_size = (max_u-min_u) / nubins
    vbin_size = (max_v-min_v) / nvbins
    max_sep = min_sep * np.exp(nrbins*bin_size)
    log_min_sep = np.log(min_sep)
    for i in range(ngal):
        for j in range(ngal):
            for k in range(ngal):
                dij = np.sqrt((x1[i]-x2[j])**2 + (y1[i]-y2[j])**2 + (z1[i]-z2[j])**2)
                dik = np.sqrt((x1[i]-x3[k])**2 + (y1[i]-y3[k])**2 + (z1[i]-z3[k])**2)
                djk = np.sqrt((x2[j]-x3[k])**2 + (y2[j]-y3[k])**2 + (z2[j]-z3[k])**2)
                if dij == 0.: continue
                if dik == 0.: continue
                if djk == 0.: continue
                if dij < dik:
                    if dik < djk:
                        d3 = dij; d2 = dik; d1 = djk
                        ccw = is_ccw_3d(x1[i],y1[i],z1[i],x2[j],y2[j],z2[j],x3[k],y3[k],z3[k])
                        true_ntri = true_ntri_123
                        true_zeta = true_zeta_123
                        true_weight = true_weight_123
                    elif dij < djk:
                        d3 = dij; d2 = djk; d1 = dik
                        ccw = is_ccw_3d(x2[j],y2[j],z2[j],x1[i],y1[i],z1[i],x3[k],y3[k],z3[k])
                        true_ntri = true_ntri_213
                        true_zeta = true_zeta_213
                        true_weight = true_weight_213
                    else:
                        d3 = djk; d2 = dij; d1 = dik
                        ccw = is_ccw_3d(x2[j],y2[j],z2[j],x3[k],y3[k],z3[k],x1[i],y1[i],z1[i])
                        true_ntri = true_ntri_231
                        true_zeta = true_zeta_231
                        true_weight = true_weight_231
                else:
                    if dij < djk:
                        d3 = dik; d2 = dij; d1 = djk
                        ccw = is_ccw_3d(x1[i],y1[i],z1[i],x3[k],y3[k],z3[k],x2[j],y2[j],z2[j])
                        true_ntri = true_ntri_132
                        true_zeta = true_zeta_132
                        true_weight = true_weight_132
                    elif dik < djk:
                        d3 = dik; d2 = djk; d1 = dij
                        ccw = is_ccw_3d(x3[k],y3[k],z3[k],x1[i],y1[i],z1[i],x2[j],y2[j],z2[j])
                        true_ntri = true_ntri_312
                        true_zeta = true_zeta_312
                        true_weight = true_weight_312
                    else:
                        d3 = djk; d2 = dik; d1 = dij
                        ccw = is_ccw_3d(x3[k],y3[k],z3[k],x2[j],y2[j],z2[j],x1[i],y1[i],z1[i])
                        true_ntri = true_ntri_321
                        true_zeta = true_zeta_321
                        true_weight = true_weight_321

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
                assert 0 <= kr < nrbins
                assert 0 <= ku < nubins
                assert 0 <= kv < 2*nvbins
                www = w1[i] * w2[j] * w3[k]
                zeta = www * k1[i] * k2[j] * k3[k]
                true_ntri[kr,ku,kv] += 1
                true_weight[kr,ku,kv] += www
                true_zeta[kr,ku,kv] += zeta

    n_list = [true_ntri_123, true_ntri_132, true_ntri_213, true_ntri_231,
              true_ntri_312, true_ntri_321]
    w_list = [true_weight_123, true_weight_132, true_weight_213, true_weight_231,
              true_weight_312, true_weight_321]
    z_list = [true_zeta_123, true_zeta_132, true_zeta_213, true_zeta_231,
              true_zeta_312, true_zeta_321]

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = sum(n_list)
    true_weight_sum = sum(w_list)
    true_zeta_sum = sum(z_list)
    pos = true_weight_sum > 0
    true_zeta_sum[pos] /= true_weight_sum[pos]
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-5)

    # Now normalize each one individually.
    for w,z in zip(w_list, z_list):
        pos = w > 0
        z[pos] /= w[pos]

    # With ordered=True, we get just the ones in this order.
    kkk.process(cat1, cat2, cat3, ordered=True, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)

    # Repeat with binslop = 0
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1)
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)

    # And again with no top-level recursion
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nrbins,
                                  min_u=min_u, max_u=max_u, nubins=nubins,
                                  min_v=min_v, max_v=max_v, nvbins=nvbins,
                                  bin_slop=0, verbose=1, max_top=0)
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-5)


@timer
def test_constant():
    # A fairly trivial test is to use a constant value of kappa everywhere.

    ngal = 500
    A = 0.05
    L = 100.
    rng = np.random.RandomState(8675309)
    x = (rng.random_sample(ngal)-0.5) * L
    y = (rng.random_sample(ngal)-0.5) * L
    kappa = A * np.ones(ngal)

    cat = treecorr.Catalog(x=x, y=y, k=kappa, x_units='arcmin', y_units='arcmin')

    min_sep = 10.
    max_sep = 25.
    nbins = 5
    min_u = 0.6
    max_u = 0.9
    nubins = 3
    min_v = 0.5
    max_v = 0.9
    nvbins = 5
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins,
                                  sep_units='arcmin', verbose=1)
    kkk.process(cat)
    print('kkk.zeta = ',kkk.zeta.flatten())
    np.testing.assert_allclose(kkk.zeta, A**3, rtol=1.e-5)

    # Should also work as a cross-correlation
    kkk.process(cat, cat, cat)
    print('as cross-correlation: kkk.zeta = ',kkk.zeta.flatten())
    np.testing.assert_allclose(kkk.zeta, A**3, rtol=1.e-5)

    kkk.process(cat, cat, cat, ordered=True)
    print('as cross-correlation ordered: kkk.zeta = ',kkk.zeta.flatten())
    np.testing.assert_allclose(kkk.zeta, A**3, rtol=1.e-5)

    # Check LogSAS binning
    kkk2 = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   nphi_bins=nubins, sep_units='arcmin', bin_type='LogSAS')
    kkk2.process(cat)
    print('LogSAS: kkk.zeta = ',kkk2.zeta.flatten())
    np.testing.assert_allclose(kkk2.zeta, A**3, rtol=1.e-5)

    kkk2.process(cat, cat)
    print('as cross-correlation: kkk.zeta = ',kkk2.zeta.flatten())
    np.testing.assert_allclose(kkk2.zeta, A**3, rtol=1.e-5)

    kkk2.process(cat, cat, ordered=True)
    print('as cross-correlation ordered: kkk.zeta = ',kkk2.zeta.flatten())
    np.testing.assert_allclose(kkk2.zeta, A**3, rtol=1.e-5)

    # Now add some noise to the values. It should still work, but at slightly lower accuracy.
    kappa += 0.001 * (rng.random_sample(ngal)-0.5)
    cat = treecorr.Catalog(x=x, y=y, k=kappa, x_units='arcmin', y_units='arcmin')
    kkk.process(cat)
    print('with noise: kkk.zeta = ',kkk.zeta.flatten())
    np.testing.assert_allclose(kkk.zeta, A**3, rtol=3.e-3)

    kkk2.process(cat)
    print('LogSAS with noise: kkk.zeta = ',kkk2.zeta.flatten())
    np.testing.assert_allclose(kkk2.zeta, A**3, rtol=3.e-3)


@timer
def test_kkk_logruv():
    # Use kappa(r) = A exp(-r^2/2s^2)
    #
    # The Fourier transform is: kappa~(k) = 2 pi A s^2 exp(-s^2 k^2/2) / L^2
    #
    # B(k1,k2) = <k~(k1) k~(k2) k~(-k1-k2)>
    #          = (2 pi A (s/L)^2)^3 exp(-s^2 (|k1|^2 + |k2|^2 - k1.k2))
    #          = (2 pi A (s/L)^2)^3 exp(-s^2 (|k1|^2 + |k2|^2 + |k3|^2)/2)
    #
    # zeta(r1,r2) = (1/2pi)^4 int(d^2k1 int(d^2k2 exp(ik1.x1) exp(ik2.x2) B(k1,k2) ))
    #             = 2/3 pi A^3 (s/L)^2 exp(-(x1^2 + y1^2 + x2^2 + y2^2 - x1x2 - y1y2)/3s^2)
    #             = 2/3 pi A^3 (s/L)^2 exp(-(d1^2 + d2^2 + d3^2)/6s^2)

    A = 0.05
    s = 10.
    if __name__ == '__main__':
        ngal = 200000
        L = 30. * s  # Not infinity, so this introduces some error.  Our integrals were to infinity.
        tol_factor = 1
    else:
        # Looser tests from nosetests that don't take so long to run.
        ngal = 5000
        L = 10. * s
        tol_factor = 5
    rng = np.random.RandomState(8675309)
    x = (rng.random_sample(ngal)-0.5) * L
    y = (rng.random_sample(ngal)-0.5) * L
    r2 = (x**2 + y**2)/s**2
    kappa = A * np.exp(-r2/2.)

    min_sep = 11.
    max_sep = 15.
    nbins = 3
    min_u = 0.7
    max_u = 1.0
    nubins = 3
    min_v = 0.1
    max_v = 0.3
    nvbins = 2

    cat = treecorr.Catalog(x=x, y=y, k=kappa, x_units='arcmin', y_units='arcmin')
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                  nubins=nubins, nvbins=nvbins,
                                  sep_units='arcmin', verbose=1)
    kkk.process(cat, num_threads=1)

    # Using bin_size=None rather than omiting bin_size is equivalent.
    # (The result is only identical if num_threads=1 though.)
    kkk2 = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins, bin_size=None,
                                   min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                   nubins=nubins, nvbins=nvbins,
                                   sep_units='arcmin', verbose=1)
    kkk2.process(cat, num_threads=1)
    assert kkk2 == kkk

    # log(<d>) != <logd>, but it should be close:
    print('meanlogd1 - log(meand1) = ',kkk.meanlogd1 - np.log(kkk.meand1))
    print('meanlogd2 - log(meand2) = ',kkk.meanlogd2 - np.log(kkk.meand2))
    print('meanlogd3 - log(meand3) = ',kkk.meanlogd3 - np.log(kkk.meand3))
    print('meand3 / meand2 = ',kkk.meand3 / kkk.meand2)
    print('meanu = ',kkk.meanu)
    print('max diff = ',np.max(np.abs(kkk.meand3/kkk.meand2 -kkk.meanu)))
    print('max rel diff = ',np.max(np.abs((kkk.meand3/kkk.meand2 -kkk.meanu)/kkk.meanu)))
    print('(meand1 - meand2)/meand3 = ',(kkk.meand1-kkk.meand2) / kkk.meand3)
    print('meanv = ',kkk.meanv)
    print('max diff = ',np.max(np.abs((kkk.meand1-kkk.meand2)/kkk.meand3 -np.abs(kkk.meanv))))
    print('max rel diff = ',np.max(np.abs(((kkk.meand1-kkk.meand2)/kkk.meand3-np.abs(kkk.meanv))
                                          / kkk.meanv)))
    np.testing.assert_allclose(kkk.meanlogd1, np.log(kkk.meand1), rtol=1.e-3)
    np.testing.assert_allclose(kkk.meanlogd2, np.log(kkk.meand2), rtol=1.e-3)
    np.testing.assert_allclose(kkk.meanlogd3, np.log(kkk.meand3), rtol=1.e-3)
    np.testing.assert_allclose(kkk.meand3/kkk.meand2, kkk.meanu, rtol=1.e-5 * tol_factor)
    np.testing.assert_allclose(np.abs(kkk.meand1-kkk.meand2)/kkk.meand3, np.abs(kkk.meanv),
                               rtol=1.e-5 * tol_factor, atol=1.e-5 * tol_factor)
    np.testing.assert_allclose(kkk.meanlogd3-kkk.meanlogd2, np.log(kkk.meanu),
                               atol=1.e-3 * tol_factor)
    np.testing.assert_allclose(np.log(np.abs(kkk.meand1-kkk.meand2))-kkk.meanlogd3,
                               np.log(np.abs(kkk.meanv)), atol=2.e-3 * tol_factor)

    d1 = kkk.meand1
    d2 = kkk.meand2
    d3 = kkk.meand3
    #print('rnom = ',np.exp(kkk.logr))
    #print('unom = ',kkk.u)
    #print('vnom = ',kkk.v)
    #print('d1 = ',d1)
    #print('d2 = ',d2)
    #print('d3 = ',d3)
    # The L^2 term in the denominator of true_zeta is the area over which the integral is done.
    # Since the centers of the triangles don't go to the edge of the box, we approximate the
    # correct area by subtracting off 2d2 from L, which should give a slightly better estimate
    # of the correct area to use here.
    L = L - 2.*d2
    true_zeta = (2.*np.pi/3) * A**3 * (s/L)**2 * np.exp(-(d1**2+d2**2+d3**2)/(6.*s**2))

    #print('ntri = ',kkk.ntri)
    print('zeta = ',kkk.zeta)
    print('true_zeta = ',true_zeta)
    #print('ratio = ',kkk.zeta / true_zeta)
    #print('diff = ',kkk.zeta - true_zeta)
    print('max rel diff = ',np.max(np.abs((kkk.zeta - true_zeta)/true_zeta)))
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=0.1 * tol_factor)
    np.testing.assert_allclose(np.log(np.abs(kkk.zeta)), np.log(np.abs(true_zeta)),
                               atol=0.1 * tol_factor)

    # Check that we get the same result using the corr3 functin:
    cat.write(os.path.join('data','kkk_data.dat'))
    config = treecorr.config.read_config('configs/kkk.yaml')
    config['verbose'] = 0
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','kkk.out'), names=True, skip_header=1)
    np.testing.assert_almost_equal(corr3_output['zeta'], kkk.zeta.flatten())

    # Check the fits write option
    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name = os.path.join('output','kkk_out.fits')
        kkk.write(out_file_name)
        data = fitsio.read(out_file_name)
        np.testing.assert_almost_equal(data['r_nom'], np.exp(kkk.logr).flatten())
        np.testing.assert_almost_equal(data['u_nom'], kkk.u.flatten())
        np.testing.assert_almost_equal(data['v_nom'], kkk.v.flatten())
        np.testing.assert_almost_equal(data['meand1'], kkk.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], kkk.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], kkk.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], kkk.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], kkk.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], kkk.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanu'], kkk.meanu.flatten())
        np.testing.assert_almost_equal(data['meanv'], kkk.meanv.flatten())
        np.testing.assert_almost_equal(data['zeta'], kkk.zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(kkk.varzeta.flatten()))
        np.testing.assert_almost_equal(data['weight'], kkk.weight.flatten())
        np.testing.assert_almost_equal(data['ntri'], kkk.ntri.flatten())

        # Check the read function
        # Note: These don't need the flatten.
        # The read function should reshape them to the right shape.
        kkk2 = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_u=min_u, max_u=max_u, min_v=min_v, max_v=max_v,
                                       nubins=nubins, nvbins=nvbins,
                                       sep_units='arcmin', verbose=1)
        kkk2.read(out_file_name)
        np.testing.assert_almost_equal(kkk2.logr, kkk.logr)
        np.testing.assert_almost_equal(kkk2.u, kkk.u)
        np.testing.assert_almost_equal(kkk2.v, kkk.v)
        np.testing.assert_almost_equal(kkk2.meand1, kkk.meand1)
        np.testing.assert_almost_equal(kkk2.meanlogd1, kkk.meanlogd1)
        np.testing.assert_almost_equal(kkk2.meand2, kkk.meand2)
        np.testing.assert_almost_equal(kkk2.meanlogd2, kkk.meanlogd2)
        np.testing.assert_almost_equal(kkk2.meand3, kkk.meand3)
        np.testing.assert_almost_equal(kkk2.meanlogd3, kkk.meanlogd3)
        np.testing.assert_almost_equal(kkk2.meanu, kkk.meanu)
        np.testing.assert_almost_equal(kkk2.meanv, kkk.meanv)
        np.testing.assert_almost_equal(kkk2.zeta, kkk.zeta)
        np.testing.assert_almost_equal(kkk2.varzeta, kkk.varzeta)
        np.testing.assert_almost_equal(kkk2.weight, kkk.weight)
        np.testing.assert_almost_equal(kkk2.ntri, kkk.ntri)
        assert kkk2.coords == kkk.coords
        assert kkk2.metric == kkk.metric
        assert kkk2.sep_units == kkk.sep_units
        assert kkk2.bin_type == kkk.bin_type

@timer
def test_direct_logsas():
    # If the catalogs are small enough, we can do a direct calculation to see if comes out right.
    # This should exactly match the treecorr result if brute=True.

    ngal = 100
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) )
    w = rng.random_sample(ngal)
    kap = rng.normal(0,sig_kap, (ngal,) )

    cat = treecorr.Catalog(x=x, y=y, w=w, k=kap)

    min_sep = 1.
    max_sep = 10.
    nbins = 10
    nphi_bins = 10
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  nphi_bins=nphi_bins, phi_units='rad',
                                  brute=True, bin_type='LogSAS')
    kkk.process(cat, num_threads=2)

    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = np.pi/nphi_bins
    true_ntri = np.zeros((nbins, nbins, nphi_bins), dtype=int)
    true_weight = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_zeta = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    for i in range(ngal):
        for j in range(ngal):
            if i == j: continue
            for k in range(ngal):
                if k == i: continue
                if k == j: continue
                # i is the vertex where phi is (aka c1)
                # ik is r2, ij is r3.
                r1 = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2)
                r2 = np.sqrt((x[i]-x[k])**2 + (y[i]-y[k])**2)
                r3 = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2)
                if r1 == 0.: continue
                if r2 == 0.: continue
                if r3 == 0.: continue
                phi = np.arccos((r2**2 + r3**2 - r1**2)/(2*r2*r3))
                if not is_ccw(x[i],y[i],x[k],y[k],x[j],y[j]):
                    phi = 2*np.pi - phi
                if r2 < min_sep or r2 >= max_sep: continue
                if r3 < min_sep or r3 >= max_sep: continue
                if phi < 0 or phi > np.pi: continue
                kr2 = int(np.floor( (np.log(r2)-log_min_sep) / bin_size ))
                kr3 = int(np.floor( (np.log(r3)-log_min_sep) / bin_size ))
                kphi = int(np.floor( phi / phi_bin_size ))
                assert 0 <= kr2 < nbins
                assert 0 <= kr3 < nbins
                assert 0 <= kphi < nphi_bins

                www = w[i] * w[j] * w[k]
                zeta = www * kap[i] * kap[j] * kap[k]

                true_ntri[kr2,kr3,kphi] += 1
                true_weight[kr2,kr3,kphi] += www
                true_zeta[kr2,kr3,kphi] += zeta

    pos = true_weight > 0
    true_zeta[pos] /= true_weight[pos]

    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/kkk_direct_logsas.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['kkk_file_name'])
        np.testing.assert_allclose(data['d2_nom'], kkk.d2nom.flatten())
        np.testing.assert_allclose(data['d3_nom'], kkk.d3nom.flatten())
        np.testing.assert_allclose(data['phi_nom'], kkk.phi.flatten())
        np.testing.assert_allclose(data['ntri'], kkk.ntri.flatten())
        np.testing.assert_allclose(data['weight'], kkk.weight.flatten())
        np.testing.assert_allclose(data['zeta'], kkk.zeta.flatten(), rtol=1.e-3)

    # Also check the cross calculation.
    # Here, we get 6x as many triangles, since each triangle is discovered 6 times.
    kkk.process(cat, cat, cat, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, 6*true_ntri)
    np.testing.assert_allclose(kkk.weight, 6*true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # But with ordered=True, it only counts each triangle once.
    kkk.process(cat,cat,cat, ordered=True, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Or with 2 argument version, finds each triangle 3 times.
    kkk.process(cat,cat)
    np.testing.assert_array_equal(kkk.ntri, 3*true_ntri)
    np.testing.assert_allclose(kkk.weight, 3*true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  nphi_bins=nphi_bins, bin_slop=0, max_top=0, bin_type='LogSAS')
    kkk.process(cat)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    kkk.process(cat,cat, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-5, atol=1.e-8)

    # Test I/O
    ascii_name = 'output/kkk_ascii_logsas.txt'
    kkk.write(ascii_name, precision=16)
    kkk3 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nbins,
                                   nphi_bins=nphi_bins, bin_type='LogSAS')
    kkk3.read(ascii_name)
    np.testing.assert_allclose(kkk3.ntri, kkk.ntri)
    np.testing.assert_allclose(kkk3.weight, kkk.weight)
    np.testing.assert_allclose(kkk3.meand1, kkk.meand1)
    np.testing.assert_allclose(kkk3.meand2, kkk.meand2)
    np.testing.assert_allclose(kkk3.meand3, kkk.meand3)
    np.testing.assert_allclose(kkk3.meanlogd1, kkk.meanlogd1)
    np.testing.assert_allclose(kkk3.meanlogd2, kkk.meanlogd2)
    np.testing.assert_allclose(kkk3.meanlogd3, kkk.meanlogd3)
    np.testing.assert_allclose(kkk3.meanphi, kkk.meanphi)
    np.testing.assert_allclose(kkk3.zeta, kkk.zeta)

    try:
        import fitsio
    except ImportError:
        pass
    else:
        fits_name = 'output/kkk_fits_logsas.fits'
        kkk.write(fits_name)
        kkk4 = treecorr.KKKCorrelation(min_sep=min_sep, bin_size=bin_size, nbins=nbins,
                                       nphi_bins=nphi_bins, bin_type='LogSAS')
        kkk4.read(fits_name)
        np.testing.assert_allclose(kkk4.ntri, kkk.ntri)
        np.testing.assert_allclose(kkk4.weight, kkk.weight)
        np.testing.assert_allclose(kkk4.meand1, kkk.meand1)
        np.testing.assert_allclose(kkk4.meand2, kkk.meand2)
        np.testing.assert_allclose(kkk4.meand3, kkk.meand3)
        np.testing.assert_allclose(kkk4.meanlogd1, kkk.meanlogd1)
        np.testing.assert_allclose(kkk4.meanlogd2, kkk.meanlogd2)
        np.testing.assert_allclose(kkk4.meanlogd3, kkk.meanlogd3)
        np.testing.assert_allclose(kkk4.meanphi, kkk.meanphi)
        np.testing.assert_allclose(kkk4.zeta, kkk.zeta)


@timer
def test_direct_logsas_spherical():
    # Repeat in spherical coords

    ngal = 100
    s = 10.
    rng = np.random.RandomState(8675309)
    x = rng.normal(0,s, (ngal,) )
    y = rng.normal(0,s, (ngal,) ) + 20  # Make sure covers a reasonalby large angle on the sky
    z = rng.normal(0,s, (ngal,) )       # so the spherical geometry matters.
    w = rng.random_sample(ngal)
    kap = rng.normal(0,3, (ngal,) )
    #w = np.ones_like(w)

    ra, dec = coord.CelestialCoord.xyz_to_radec(x,y,z)

    cat = treecorr.Catalog(ra=ra, dec=dec, ra_units='rad', dec_units='rad', w=w, k=kap)

    min_sep = 5.
    max_sep = 100.
    nbins = 3
    nphi_bins = 6
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, sep_units='deg',
                                  nbins=nbins, nphi_bins=nphi_bins, phi_units='deg',
                                  brute=True, bin_type='LogSAS')
    kkk.process(cat)

    r = np.sqrt(x**2 + y**2 + z**2)
    x /= r;  y /= r;  z /= r

    true_ntri = np.zeros((nbins, nbins, nphi_bins), dtype=int)
    true_weight = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_zeta = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand1 = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand2 = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand3 = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meanphi = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_ntri_arc = np.zeros((nbins, nbins, nphi_bins), dtype=int)
    true_weight_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_zeta_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand1_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand2_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meand3_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)
    true_meanphi_arc = np.zeros((nbins, nbins, nphi_bins), dtype=float)

    rad_min_sep = min_sep * coord.degrees / coord.radians
    rad_max_sep = max_sep * coord.degrees / coord.radians
    bin_size = np.log(max_sep / min_sep) / nbins
    phi_bin_size = np.pi/nphi_bins
    for i in range(ngal):
        for j in range(ngal):
            if i == j: continue
            for k in range(ngal):
                if k == i: continue
                if k == j: continue
                # i is the vertex where phi is (aka c1)
                # ik is d2, ij is d3.
                d1 = np.sqrt((x[j]-x[k])**2 + (y[j]-y[k])**2 + (z[j]-z[k])**2)
                d2 = np.sqrt((x[k]-x[i])**2 + (y[k]-y[i])**2 + (z[k]-z[i])**2)
                d3 = np.sqrt((x[i]-x[j])**2 + (y[i]-y[j])**2 + (z[i]-z[j])**2)
                if d1 == 0.: continue
                if d2 == 0.: continue
                if d3 == 0.: continue
                phi = np.arccos((d2**2 + d3**2 - d1**2) / (2*d2*d3))
                if not is_ccw_3d(x[i],y[i],z[i],x[k],y[k],z[k],x[j],y[j],z[j]):
                    phi = 2*np.pi - phi

                www = w[i] * w[j] * w[k]
                zeta = www * kap[i] * kap[j] * kap[k]

                if ( (rad_min_sep <= d2 < rad_max_sep) and
                     (rad_min_sep <= d3 < rad_max_sep) and
                     0 <= phi < np.pi):
                    kr2 = int(np.floor(np.log(d2/rad_min_sep) / bin_size))
                    kr3 = int(np.floor(np.log(d3/rad_min_sep) / bin_size))
                    kphi = int(np.floor( phi / phi_bin_size ))
                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    assert 0 <= kphi < nphi_bins

                    true_ntri[kr2,kr3,kphi] += 1
                    true_weight[kr2,kr3,kphi] += www
                    true_zeta[kr2,kr3,kphi] += zeta
                    true_meand1[kr2,kr3,kphi] += www * d1
                    true_meand2[kr2,kr3,kphi] += www * d2
                    true_meand3[kr2,kr3,kphi] += www * d3
                    true_meanphi[kr2,kr3,kphi] += www * phi

                # For Arc metric, use spherical geometry for phi definition.
                # Law of cosines in spherical geom:
                # cos(c) = cos(a) cos(b) + sin(a) sin(b) cos(phi)
                # We need to convert the above chord distanes to great circle angles.
                a = 2*np.arcsin(d2/2)
                b = 2*np.arcsin(d3/2)
                c = 2*np.arcsin(d1/2)
                phi = np.arccos((np.cos(c) - np.cos(a)*np.cos(b)) / (np.sin(a)*np.sin(b)))

                if not is_ccw_3d(x[i],y[i],z[i],x[k],y[k],z[k],x[j],y[j],z[j]):
                    phi = 2*np.pi - phi

                if ( (rad_min_sep <= a < rad_max_sep) and
                     (rad_min_sep <= b < rad_max_sep) and
                     0 <= phi < np.pi):
                    kr2 = int(np.floor(np.log(a/rad_min_sep) / bin_size))
                    kr3 = int(np.floor(np.log(b/rad_min_sep) / bin_size))
                    kphi = int(np.floor( phi / phi_bin_size ))

                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    assert 0 <= kphi < nphi_bins

                    true_ntri_arc[kr2,kr3,kphi] += 1
                    true_weight_arc[kr2,kr3,kphi] += www
                    true_zeta_arc[kr2,kr3,kphi] += zeta
                    true_meand1_arc[kr2,kr3,kphi] += www * c
                    true_meand2_arc[kr2,kr3,kphi] += www * a
                    true_meand3_arc[kr2,kr3,kphi] += www * b
                    true_meanphi_arc[kr2,kr3,kphi] += www * phi

    pos = true_weight > 0
    true_zeta[pos] /= true_weight[pos]
    true_meand1[pos] /= true_weight[pos]
    true_meand2[pos] /= true_weight[pos]
    true_meand3[pos] /= true_weight[pos]
    true_meanphi[pos] /= true_weight[pos]
    posa = true_weight_arc > 0
    true_zeta_arc[posa] /= true_weight_arc[posa]
    true_meand1_arc[posa] /= true_weight_arc[posa]
    true_meand2_arc[posa] /= true_weight_arc[posa]
    true_meand3_arc[posa] /= true_weight_arc[posa]
    true_meanphi_arc[posa] /= true_weight_arc[posa]

    # Convert chord distances and angle to spherical values (in degrees)
    # cosphi = (d2^2 + d3^2 - d1^2 - 1/2 d2^2 d3^2) / (2 d2 d3 sqrt(1-d2^2) sqrt(1-d3^2))
    # Fix this first, while the ds are still chord distances.
    cosphi = np.cos(true_meanphi)
    cosphi -= 0.25 * true_meand2 * true_meand3
    cosphi /= np.sqrt(1-0.25*true_meand2**2) * np.sqrt(1-0.25*true_meand3**2)
    true_meanphi[:] = np.arccos(cosphi) * 180./np.pi
    for dd in [true_meand1, true_meand2, true_meand3]:
        dd[:] = 2 * np.arcsin(dd/2) * 180/np.pi
    for dd in [true_meand1_arc, true_meand2_arc, true_meand3_arc, true_meanphi_arc]:
        dd *= 180. / np.pi

    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand1[pos], true_meand1[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand2[pos], true_meand2[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand3[pos], true_meand3[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meanphi[pos], true_meanphi[pos], rtol=1.e-4, atol=1.e-6)

    # Check that running via the corr3 script works correctly.
    config = treecorr.config.read_config('configs/kkk_direct_spherical_logsas.yaml')
    try:
        import fitsio
    except ImportError:
        pass
    else:
        cat.write(config['file_name'])
        treecorr.corr3(config)
        data = fitsio.read(config['kkk_file_name'])
        np.testing.assert_allclose(data['d2_nom'], kkk.d2nom.flatten())
        np.testing.assert_allclose(data['d3_nom'], kkk.d3nom.flatten())
        np.testing.assert_allclose(data['phi_nom'], kkk.phi.flatten())
        np.testing.assert_allclose(data['ntri'], kkk.ntri.flatten())
        np.testing.assert_allclose(data['weight'], kkk.weight.flatten())
        np.testing.assert_allclose(data['zeta'], kkk.zeta.flatten(), rtol=1.e-3)

    # Repeat with binslop = 0
    # And don't do any top-level recursion so we actually test not going to the leaves.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, sep_units='deg',
                                  nbins=nbins, nphi_bins=nphi_bins, phi_units='deg',
                                  bin_slop=0, max_top=0, bin_type='LogSAS')
    kkk.process(cat)
    np.testing.assert_array_equal(kkk.ntri, true_ntri)
    np.testing.assert_allclose(kkk.weight, true_weight, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand1[pos], true_meand1[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand2[pos], true_meand2[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand3[pos], true_meand3[pos], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meanphi[pos], true_meanphi[pos], rtol=1.e-4, atol=1.e-6)

    # Now do Arc metric, where distances and angles use spherical geometry.
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, sep_units='deg',
                                  nbins=nbins, nphi_bins=nphi_bins, phi_units='deg',
                                  bin_slop=0, bin_type='LogSAS', metric='Arc')
    kkk.process(cat, num_threads=1)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_arc)
    np.testing.assert_allclose(kkk.weight, true_weight_arc, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta_arc, rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand1[posa], true_meand1_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand2[posa], true_meand2_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand3[posa], true_meand3_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meanphi[posa], true_meanphi_arc[posa], rtol=1.e-4, atol=1.e-6)

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, sep_units='deg',
                                  nbins=nbins, nphi_bins=nphi_bins, phi_units='deg',
                                  bin_slop=0, max_top=0, bin_type='LogSAS', metric='Arc')
    kkk.process(cat)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_arc)
    np.testing.assert_allclose(kkk.weight, true_weight_arc, rtol=1.e-5, atol=1.e-8)
    np.testing.assert_allclose(kkk.zeta, true_zeta_arc, rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand1[posa], true_meand1_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand2[posa], true_meand2_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meand3[posa], true_meand3_arc[posa], rtol=1.e-4, atol=1.e-6)
    np.testing.assert_allclose(kkk.meanphi[posa], true_meanphi_arc[posa], rtol=1.e-4, atol=1.e-6)


@timer
def test_direct_logsas_cross():
    # If the catalogs are small enough, we can do a direct calculation to see if comes out right.
    # This should exactly match the treecorr result if brute=True.

    ngal = 50
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    w1 = rng.random_sample(ngal).astype(np.float32)
    k1 = rng.normal(0,sig_kap, (ngal,) ).astype(np.float32)
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    w2 = rng.random_sample(ngal).astype(np.float32)
    k2 = rng.normal(0,sig_kap, (ngal,) ).astype(np.float32)
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2)
    x3 = rng.normal(0,s, (ngal,) )
    y3 = rng.normal(0,s, (ngal,) )
    w3 = rng.random_sample(ngal).astype(np.float32)
    k3 = rng.normal(0,sig_kap, (ngal,) ).astype(np.float32)
    cat3 = treecorr.Catalog(x=x3, y=y3, w=w3, k=k3)

    min_sep = 1.
    max_sep = 10.
    nbins = 10
    nphi_bins = 10

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep,
                                  nbins=nbins, nphi_bins=nphi_bins,
                                  brute=True, bin_type='LogSAS')
    kkk.process(cat1, cat2, cat3, num_threads=2)

    # Figure out the correct answer for each permutation
    true_ntri_123 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_132 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_213 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_231 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_312 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_321 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_123 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_132 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_213 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_231 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_312 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_321 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_123 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_132 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_213 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_231 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_312 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_321 = np.zeros( (nbins, nbins, nphi_bins) )
    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = np.pi / nphi_bins
    log_min_sep = np.log(min_sep)
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

                www = w1[i] * w2[j] * w3[k]
                zeta = www * k1[i] * k2[j] * k3[k]

                if d2 >= min_sep and d2 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    # 123
                    phi = np.arccos((d2**2 + d3**2 - d1**2)/(2*d2*d3))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_123[kr2,kr3,kphi] += 1
                        true_weight_123[kr2,kr3,kphi] += www
                        true_zeta_123[kr2,kr3,kphi] += zeta

                    phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_132[kr3,kr2,kphi] += 1
                        true_weight_132[kr3,kr2,kphi] += www
                        true_zeta_132[kr3,kr2,kphi] += zeta

                if d1 >= min_sep and d1 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr3 < nbins
                    # 231
                    phi = np.arccos((d1**2 + d3**2 - d2**2)/(2*d1*d3))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_231[kr3,kr1,kphi] += 1
                        true_weight_231[kr3,kr1,kphi] += www
                        true_zeta_231[kr3,kr1,kphi] += zeta

                    # 213
                    phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_213[kr1,kr3,kphi] += 1
                        true_weight_213[kr1,kr3,kphi] += www
                        true_zeta_213[kr1,kr3,kphi] += zeta

                if d1 >= min_sep and d1 < max_sep and d2 >= min_sep and d2 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr2 < nbins
                    # 312
                    phi = np.arccos((d1**2 + d2**2 - d3**2)/(2*d1*d2))
                    if not is_ccw(x1[i],y1[i],x3[k],y3[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_312[kr1,kr2,kphi] += 1
                        true_weight_312[kr1,kr2,kphi] += www
                        true_zeta_312[kr1,kr2,kphi] += zeta

                    # 321
                    phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_321[kr2,kr1,kphi] += 1
                        true_weight_321[kr2,kr1,kphi] += www
                        true_zeta_321[kr2,kr1,kphi] += zeta

    n_list = [true_ntri_123, true_ntri_132, true_ntri_213, true_ntri_231,
              true_ntri_312, true_ntri_321]
    w_list = [true_weight_123, true_weight_132, true_weight_213, true_weight_231,
              true_weight_312, true_weight_321]
    z_list = [true_zeta_123, true_zeta_132, true_zeta_213, true_zeta_231,
              true_zeta_312, true_zeta_321]

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = sum(n_list)
    true_weight_sum = sum(w_list)
    true_zeta_sum = sum(z_list)
    pos = true_weight_sum > 0
    true_zeta_sum[pos] /= true_weight_sum[pos]
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-4, atol=1.e-6)

    # Now normalize each one individually.
    for w,z in zip(w_list, z_list):
        pos = w > 0
        z[pos] /= w[pos]

    # With ordered=True we get just the ones in the given order.
    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat1, cat3, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_132)
    np.testing.assert_allclose(kkk.weight, true_weight_132, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_132, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat1, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_213)
    np.testing.assert_allclose(kkk.weight, true_weight_213, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_213, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat3, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_231)
    np.testing.assert_allclose(kkk.weight, true_weight_231, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_231, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat3, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_312)
    np.testing.assert_allclose(kkk.weight, true_weight_312, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_312, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat3, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_321)
    np.testing.assert_allclose(kkk.weight, true_weight_321, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_321, rtol=1.e-4, atol=1.e-6)

    # Repeat with binslop = 0
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep,
                                  nbins=nbins, nphi_bins=nphi_bins,
                                  bin_slop=0, bin_type='LogSAS')
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-4, atol=1.e-6)

    # And again with no top-level recursion
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep,
                                  nbins=nbins, nphi_bins=nphi_bins,
                                  bin_slop=0, max_top=0, bin_type='LogSAS')
    kkk.process(cat1, cat2, cat3)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)

    kkk.process(cat1, cat2, cat3, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_123)
    np.testing.assert_allclose(kkk.weight, true_weight_123, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_123, rtol=1.e-4, atol=1.e-6)

    # Error to have cat3, but not cat2
    with assert_raises(ValueError):
        kkk.process(cat1, cat3=cat3)


@timer
def test_direct_logsas_cross12():
    # Check the 1-2 cross correlation

    ngal = 50
    s = 10.
    sig_kap = 3
    rng = np.random.RandomState(8675309)
    x1 = rng.normal(0,s, (ngal,) )
    y1 = rng.normal(0,s, (ngal,) )
    w1 = rng.random_sample(ngal)
    k1 = rng.normal(0,sig_kap, (ngal,) )
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1)
    x2 = rng.normal(0,s, (ngal,) )
    y2 = rng.normal(0,s, (ngal,) )
    w2 = rng.random_sample(ngal)
    k2 = rng.normal(0,sig_kap, (ngal,) )
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2)

    min_sep = 1.
    max_sep = 10.
    nbins = 10
    nphi_bins = 10

    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep,
                                  nbins=nbins, nphi_bins=nphi_bins,
                                  bin_slop=0, bin_type='LogSAS')
    kkk.process(cat1, cat2, num_threads=2)

    # Figure out the correct answer for each permutation
    true_ntri_122 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_212 = np.zeros( (nbins, nbins, nphi_bins) )
    true_ntri_221 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_122 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_212 = np.zeros( (nbins, nbins, nphi_bins) )
    true_zeta_221 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_122 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_212 = np.zeros( (nbins, nbins, nphi_bins) )
    true_weight_221 = np.zeros( (nbins, nbins, nphi_bins) )
    log_min_sep = np.log(min_sep)
    log_max_sep = np.log(max_sep)
    bin_size = (log_max_sep - log_min_sep) / nbins
    phi_bin_size = np.pi / nphi_bins
    log_min_sep = np.log(min_sep)
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

                www = w1[i] * w2[j] * w2[k]
                zeta = www * k1[i] * k2[j] * k2[k]

                # 123
                if d2 >= min_sep and d2 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr2 < nbins
                    assert 0 <= kr3 < nbins
                    phi = np.arccos((d2**2 + d3**2 - d1**2)/(2*d2*d3))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_122[kr2,kr3,kphi] += 1
                        true_weight_122[kr2,kr3,kphi] += www
                        true_zeta_122[kr2,kr3,kphi] += zeta

                # 231
                if d1 >= min_sep and d1 < max_sep and d3 >= min_sep and d3 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr3 < nbins
                    phi = np.arccos((d1**2 + d3**2 - d2**2)/(2*d1*d3))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_221[kr3,kr1,kphi] += 1
                        true_weight_221[kr3,kr1,kphi] += www
                        true_zeta_221[kr3,kr1,kphi] += zeta

                # 312
                if d1 >= min_sep and d1 < max_sep and d2 >= min_sep and d2 < max_sep:
                    assert 0 <= kr1 < nbins
                    assert 0 <= kr2 < nbins
                    phi = np.arccos((d1**2 + d2**2 - d3**2)/(2*d1*d2))
                    if not is_ccw(x1[i],y1[i],x2[k],y2[k],x2[j],y2[j]):
                        phi = 2*np.pi - phi
                    if phi >= 0 and phi < np.pi:
                        kphi = int(np.floor( phi / phi_bin_size ))
                        assert 0 <= kphi < nphi_bins
                        true_ntri_212[kr1,kr2,kphi] += 1
                        true_weight_212[kr1,kr2,kphi] += www
                        true_zeta_212[kr1,kr2,kphi] += zeta

    n_list = [true_ntri_122, true_ntri_212, true_ntri_221]
    w_list = [true_weight_122, true_weight_212, true_weight_221]
    z_list = [true_zeta_122, true_zeta_212, true_zeta_221]

    # With the default ordered=False, we end up with the sum of all permutations.
    true_ntri_sum = sum(n_list)
    true_weight_sum = sum(w_list)
    true_zeta_sum = sum(z_list)
    pos = true_weight_sum > 0
    true_zeta_sum[pos] /= true_weight_sum[pos]
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-4, atol=1.e-6)

    # Now normalize each one individually.
    for w,z in zip(w_list, z_list):
        pos = w > 0
        z[pos] /= w[pos]

    # With ordered=True we get just the ones in the given order.
    kkk.process(cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_122)
    np.testing.assert_allclose(kkk.weight, true_weight_122, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_122, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_212)
    np.testing.assert_allclose(kkk.weight, true_weight_212, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_212, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_221)
    np.testing.assert_allclose(kkk.weight, true_weight_221, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_221, rtol=1.e-4, atol=1.e-6)

    # Split into patches to test the list-based version of the code.
    cat1 = treecorr.Catalog(x=x1, y=y1, w=w1, k=k1, npatch=4)
    cat2 = treecorr.Catalog(x=x2, y=y2, w=w2, k=k2, npatch=4)

    kkk.process(cat1, cat2, num_threads=2)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_sum)
    np.testing.assert_allclose(kkk.weight, true_weight_sum, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_sum, rtol=1.e-4, atol=1.e-6)

    kkk.process(cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_122)
    np.testing.assert_allclose(kkk.weight, true_weight_122, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_122, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat1, cat2, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_212)
    np.testing.assert_allclose(kkk.weight, true_weight_212, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_212, rtol=1.e-4, atol=1.e-6)
    kkk.process(cat2, cat2, cat1, ordered=True)
    np.testing.assert_array_equal(kkk.ntri, true_ntri_221)
    np.testing.assert_allclose(kkk.weight, true_weight_221, rtol=1.e-5)
    np.testing.assert_allclose(kkk.zeta, true_zeta_221, rtol=1.e-4, atol=1.e-6)


@timer
def test_kkk_logsas():
    # Use kappa(r) = A exp(-r^2/2s^2)
    #
    # The Fourier transform is: kappa~(k) = 2 pi A s^2 exp(-s^2 k^2/2) / L^2
    #
    # B(k1,k2) = <k~(k1) k~(k2) k~(-k1-k2)>
    #          = (2 pi A (s/L)^2)^3 exp(-s^2 (|k1|^2 + |k2|^2 - k1.k2))
    #          = (2 pi A (s/L)^2)^3 exp(-s^2 (|k1|^2 + |k2|^2 + |k3|^2)/2)
    #
    # zeta(r1,r2) = (1/2pi)^4 int(d^2k1 int(d^2k2 exp(ik1.x1) exp(ik2.x2) B(k1,k2) ))
    #             = 2/3 pi A^3 (s/L)^2 exp(-(x1^2 + y1^2 + x2^2 + y2^2 - x1x2 - y1y2)/3s^2)
    #             = 2/3 pi A^3 (s/L)^2 exp(-(d1^2 + d2^2 + d3^2)/6s^2)

    A = 0.05
    s = 10.
    if __name__ == '__main__':
        ngal = 100000
        L = 20. * s  # Not infinity, so this introduces some error.  Our integrals were to infinity.
        tol_factor = 1
    else:
        # Looser tests from nosetests that don't take so long to run.
        ngal = 5000
        L = 10. * s
        tol_factor = 5
    rng = np.random.RandomState(8675309)
    x = (rng.random_sample(ngal)-0.5) * L
    y = (rng.random_sample(ngal)-0.5) * L
    r2 = (x**2 + y**2)/s**2
    kappa = A * np.exp(-r2/2.)

    min_sep = 10.
    max_sep = 13.
    nbins = 3
    min_phi = 45.
    max_phi = 90.
    nphi_bins = 5

    cat = treecorr.Catalog(x=x, y=y, k=kappa, x_units='arcmin', y_units='arcmin')
    kkk = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                  min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                  sep_units='arcmin', phi_units='deg', bin_type='LogSAS')
    t0 = time.time()
    kkk.process(cat)
    print(kkk.ntri)
    t1 = time.time()
    print('auto process time = ',t1-t0)

    # Doing 3 catalogs ordered, should be equivelant.  Not numerically identical, but
    # basically the same answer.
    kkkc = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                   min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                   sep_units='arcmin', phi_units='deg', bin_type='LogSAS')
    t0 = time.time()
    kkkc.process(cat,cat,cat, ordered=True)
    t1 = time.time()
    print('cross process time = ',t1-t0)
    print(kkk.zeta)
    print(kkkc.zeta)
    np.testing.assert_allclose(kkkc.ntri, kkk.ntri, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd1, kkk.meanlogd1, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd2, kkk.meanlogd2, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd3, kkk.meanlogd3, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanphi, kkk.meanphi, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.zeta, kkk.zeta, rtol=1.e-3)

    t0 = time.time()
    kkkc.process(cat,cat, ordered=True)
    t1 = time.time()
    print('cross12 process time = ',t1-t0)
    np.testing.assert_allclose(kkkc.ntri, kkk.ntri, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd1, kkk.meanlogd1, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd2, kkk.meanlogd2, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanlogd3, kkk.meanlogd3, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.meanphi, kkk.meanphi, rtol=1.e-3)
    np.testing.assert_allclose(kkkc.zeta, kkk.zeta, rtol=1.e-3)

    # log(<d>) != <logd>, but it should be close:
    print('meanlogd2 - log(meand2) = ',kkk.meanlogd2 - np.log(kkk.meand2))
    print('meanlogd3 - log(meand3) = ',kkk.meanlogd3 - np.log(kkk.meand3))
    np.testing.assert_allclose(kkk.meanlogd2, np.log(kkk.meand2), rtol=1.e-3)
    np.testing.assert_allclose(kkk.meanlogd3, np.log(kkk.meand3), rtol=1.e-3)

    d1 = kkk.meand1
    d2 = kkk.meand2
    d3 = kkk.meand3
    true_zeta = (2.*np.pi/3) * A**3 * (s/L)**2 * np.exp(-(d1**2+d2**2+d3**2)/(6.*s**2))

    print('true = ',true_zeta.ravel())
    print('meas = ',kkk.zeta.ravel())
    print('ratio = ',kkk.zeta.ravel()/true_zeta.ravel())
    np.testing.assert_allclose(kkk.zeta, true_zeta, rtol=0.2 * tol_factor)
    np.testing.assert_allclose(np.log(np.abs(kkk.zeta)), np.log(np.abs(true_zeta)),
                               atol=0.1 * tol_factor)

    # Check that we get the same result using the corr3 functin:
    cat.write(os.path.join('data','kkk_data_logsas.dat'))
    config = treecorr.config.read_config('configs/kkk_logsas.yaml')
    config['verbose'] = 0
    treecorr.corr3(config)
    corr3_output = np.genfromtxt(os.path.join('output','kkk_logsas.out'), names=True, skip_header=1)
    np.testing.assert_almost_equal(corr3_output['zeta'], kkk.zeta.flatten())

    # Check the fits write option
    try:
        import fitsio
    except ImportError:
        pass
    else:
        out_file_name = os.path.join('output','kkk_out_logsas.fits')
        kkk.write(out_file_name)
        data = fitsio.read(out_file_name)
        np.testing.assert_almost_equal(data['d2_nom'], np.exp(kkk.logd2).flatten())
        np.testing.assert_almost_equal(data['d3_nom'], np.exp(kkk.logd3).flatten())
        np.testing.assert_almost_equal(data['phi_nom'], kkk.phi.flatten())
        np.testing.assert_almost_equal(data['meand1'], kkk.meand1.flatten())
        np.testing.assert_almost_equal(data['meanlogd1'], kkk.meanlogd1.flatten())
        np.testing.assert_almost_equal(data['meand2'], kkk.meand2.flatten())
        np.testing.assert_almost_equal(data['meanlogd2'], kkk.meanlogd2.flatten())
        np.testing.assert_almost_equal(data['meand3'], kkk.meand3.flatten())
        np.testing.assert_almost_equal(data['meanlogd3'], kkk.meanlogd3.flatten())
        np.testing.assert_almost_equal(data['meanphi'], kkk.meanphi.flatten())
        np.testing.assert_almost_equal(data['zeta'], kkk.zeta.flatten())
        np.testing.assert_almost_equal(data['sigma_zeta'], np.sqrt(kkk.varzeta.flatten()))
        np.testing.assert_almost_equal(data['weight'], kkk.weight.flatten())
        np.testing.assert_almost_equal(data['ntri'], kkk.ntri.flatten())

        # Check the read function
        # Note: These don't need the flatten.
        # The read function should reshape them to the right shape.
        kkk2 = treecorr.KKKCorrelation(min_sep=min_sep, max_sep=max_sep, nbins=nbins,
                                       min_phi=min_phi, max_phi=max_phi, nphi_bins=nphi_bins,
                                       sep_units='arcmin', phi_units='deg', bin_type='LogSAS')
        kkk2.read(out_file_name)
        np.testing.assert_almost_equal(kkk2.logd2, kkk.logd2)
        np.testing.assert_almost_equal(kkk2.logd3, kkk.logd3)
        np.testing.assert_almost_equal(kkk2.phi, kkk.phi)
        np.testing.assert_almost_equal(kkk2.meand1, kkk.meand1)
        np.testing.assert_almost_equal(kkk2.meanlogd1, kkk.meanlogd1)
        np.testing.assert_almost_equal(kkk2.meand2, kkk.meand2)
        np.testing.assert_almost_equal(kkk2.meanlogd2, kkk.meanlogd2)
        np.testing.assert_almost_equal(kkk2.meand3, kkk.meand3)
        np.testing.assert_almost_equal(kkk2.meanlogd3, kkk.meanlogd3)
        np.testing.assert_almost_equal(kkk2.meanphi, kkk.meanphi)
        np.testing.assert_almost_equal(kkk2.zeta, kkk.zeta)
        np.testing.assert_almost_equal(kkk2.varzeta, kkk.varzeta)
        np.testing.assert_almost_equal(kkk2.weight, kkk.weight)
        np.testing.assert_almost_equal(kkk2.ntri, kkk.ntri)
        assert kkk2.coords == kkk.coords
        assert kkk2.metric == kkk.metric
        assert kkk2.sep_units == kkk.sep_units
        assert kkk2.phi_units == kkk.phi_units
        assert kkk2.bin_type == kkk.bin_type

if __name__ == '__main__':
    test_direct_logruv()
    test_direct_logruv_spherical()
    test_direct_logruv_cross()
    test_direct_logruv_cross12()
    test_direct_logruv_cross_3d()
    test_constant()
    test_kkk_logruv()
    test_direct_logsas()
    test_direct_logsas_spherical()
    test_direct_logsas_cross()
    test_direct_logsas_cross12()
    test_kkk_logsas()
