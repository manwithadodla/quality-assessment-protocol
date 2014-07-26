"""
TODO
"""

import os
import sys
import numpy as np
import nibabel as nb
import pandas as pd
import scipy.ndimage as nd
import scipy.stats as stats
from tempfile import mkdtemp

# DVARS
from dvars import mean_dvars_wrapper
from utils import remove_oblique_warning

# MeanFD
## borrowed from C-PAC
## from CPAC.generate_motion_statistics import calculate_FD_J as fd_jenkinson
def fd_jenkinson(in_file):
    '''
    @ Krsna
    May 2013
    compute
    1) Jenkinson FD from 3dvolreg's *.affmat12.1D file from -1Dmatrix_save option
    input: subject ID, rest_number, name of 6 parameter motion correction file (an output of 3dvolreg)
    output: FD_J.1D file
    Assumptions: 1) subject is available in BASE_DIR
    2) 3dvolreg is already performed and the 1D motion parameter and 1D_matrix file file is present in sub?/rest_? called as --->'lfo_mc_affmat.1D'

    Method to calculate Framewise Displacement (FD) calculations
    (Jenkinson et al., 2002)
    Parameters; in_file : string
    Returns; FDs : numpy.array
    NOTE: infile should have one 3dvolreg affine matrix in one row - NOT the motion parameters
    '''
    import numpy as np
    import os
    import sys
    import math
   
    pm_ = np.genfromtxt(in_file)
        
    pm = np.zeros((pm_.shape[0],pm_.shape[1]+4))
    pm[:,:12]=pm_
    pm[:,12:]=[0.0, 0.0, 0.0, 1.0]

    # The default radius (as in FSL) of a sphere represents the brain
    rmax = 50.0
    
    FDs = []
    T_rb_prev = np.matrix(pm[0].reshape(4,4))
    for i in range(1, pm.shape[0]):
        T_rb = np.matrix(pm[i].reshape(4,4)) # making use of the fact that the order of aff12 matrix is "row-by-row"
        M = np.dot(T_rb, T_rb_prev.I) - np.eye(4)
        A = M[0:3, 0:3]
        b = M[0:3, 3]

        FD_J = math.sqrt((rmax*rmax/5)*np.trace(np.dot(A.T, A)) + np.dot(b.T, b))
        FDs.append(FD_J)         
        T_rb_prev = T_rb
        
    return np.array(FDs)

def summarize_fd(in_file, threshold=0.2):
    # Threshold is in terms of mm, i think?
    
    # Compute FD
    fd    = fd_jenkinson(in_file)
    
    # Calculate Mean
    mean_fd     = fd.mean()
    
    # Calculate Outliers
    ## Number and Percent of frames (time points) where 
    ## movement (FD) exceeded threshold
    num_fd      = (fd>threshold).sum()
    percent_fd  = (num_fd*100.0)/(len(fd))    
    
    return (mean_fd, num_fd, percent_fd)

# 3dTout
def outlier_timepoints(func_file, mask_file, out_fraction=True):
    """
    Calculates the number of 'outliers' in a 4D functional dataset, 
    at each time-point.
    
    Will call on AFNI's 3dToutcount.
    
    Parameters
    ----------
    func_file: str
        Path to 4D functional file (could be motion corrected or not??)
    mask_file: str
        Path to functional brain mask
    out_fraction: bool (default: True)
        Whether the output should be a count (False) or fraction (True)
        of the number of masked voxels which are outliers at each time point.
    
    Returns
    -------
    outliers: list
    """
    import commands
    
    opts    = []
    if out_fraction:
        opts.append("-fraction")
    opts.append("-mask %s" % mask_file)
    opts.append(func_file)
    str_opts= " ".join(opts)
    
    # TODO:
    # check if should use -polort 2 (http://www.na-mic.org/Wiki/images/8/86/FBIRNSupplementalMaterial082005.pdf)
    # or -legendre to remove any trend
    cmd     = "3dToutcount %s" % str_opts
    out     = commands.getoutput(cmd)
    out     = remove_oblique_warning(out)

    # Extract time-series in output
    lines   = out.splitlines()
    ## remove general information
    lines   = [ l for l in lines if l[:2] != "++" ]
    
    ## string => floats
    outliers= [ float(l.strip()) for l in lines ] # note: don't really need strip
    
    return outliers

def mean_outlier_timepoints(*args, **kwrds):
    outliers        = outlier_timepoints(*args, **kwrds)
    mean_outliers   = np.mean(outliers)
    return mean_outliers


# 3dTqual
def quality_timepoints(func_file, mask=None):
    """
    Calculates a 'quality index' for each timepoint in the 4D functional dataset.
    Low values are good and indicate that the timepoint is not very different from the norm.
    """
    import subprocess
    
    opts    = []
    if mask:
        if mask=="auto":
            opts.append("-automask")
        else:
            opts.append("-mask %s"%mask)
    opts.append(func_file)
    str_opts= " ".join(opts)
    
    cmd     = "3dTqual %s" % str_opts
    p       = subprocess.Popen(cmd.split(" "), 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
    out, _ = p.communicate()
    
    #import code
    #code.interact(local=locals())
    
    # Extract time-series in output
    lines   = out.splitlines()
    ## remove general information
    lines   = [ l for l in lines if l[:2] not in "++" ]
    ## string => floats
    outliers= [ float(l.strip()) for l in lines ] # note: don't really need strip
    
    return outliers

def mean_quality_timepoints(*args, **kwrds):
    qualities       = quality_timepoints(*args, **kwrds)
    mean_qualities  = np.mean(qualities)
    return mean_qualities

def median_tsnr(func_data, mask_data):
    """ Calculates median of temporal Signal to Noise ratio within a mask"""
    
    data_std = func_data.std(axis=0)
    # exclude voxels with no variance
    std_mask = (data_std !=0)
    tsnr = func_data.mean(axis=0)[std_mask]/data_std[std_mask]
    print tsnr.shape
    
    return np.median(tsnr)
