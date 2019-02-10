# !/usr/bin/python

import pandas as pd
import numpy as np
import scipy as sp
from scipy import stats
import matplotlib
import matplotlib.pyplot as plt
import math
from matplotlib.colors import LogNorm
from matplotlib import cm
import os
import pdb
import copy
import gpmodel_library as gplib 

from analysis_utils import *

######### MAIN LOOP ###########
if __name__ == '__main__':

    # Define files for globa maxima loc, robot samples, and name. 
    # Lists should be the same length
    maxima_files = ['/home/genevieve/Downloads/true_maxima.csv',
                    '/home/genevieve/Downloads/true_maxima.csv']

    sample_files = ['/home/genevieve/Downloads/robot_model.csv',
                    '/home/genevieve/Downloads/robot_model.csv']
    labels = ['SAMPLE1',
              'SAMPLE2'] 

    # Filename for the logfile
    log_file_start = 'iros_car_trials'

    # path = '/media/genevieve/WINDOWS_COM/IROS_2019/experiments/'

    # Variables for making dataframes
    all_dfs = []
    all_sample_dfs = []
    all_props = []
    all_propsy = []
    all_labels = []
    all_errx = []
    all_errz = []
    dist_dfs = []
    dist_samples_dfs = []
    dist_props = []
    dist_propsy = []
    dist_ids = []
    dist_err_x = []
    dist_err_z = []

    max_val = []
    max_loc = []

    for label, fmax, fsamp in zip(labels, maxima_files, sample_files):
        samples = []

        print "Adding for:", label 
        # Read maxima from file
        maxima_df = pd.read_csv(fmax, sep=',',header=None)
        max_loc = np.array([maxima_df[0][0], maxima_df[0][1]]).reshape((1, 2))
        max_val = np.array(maxima_df[0][2]).reshape((1, 1))

        # Generate sample statistics
        sdata, prop, propy, err_x, err_z = make_samples_df([fsamp], ['x', 'y', 'z'], max_loc = max_loc, max_val = max_val, xthresh = 1.5, ythresh = 3.0)
        all_sample_dfs.append(sdata)
        all_props.append(prop)
        all_propsy.append(propy)
        all_labels.append(label)
        all_errx.append(err_x)
        all_errz.append(err_z)

        # Geneate data without distance truncation
        # dist_data, dist_sdata, d_props, d_propsy, ids, d_err_x, d_err_z = make_dist_dfs(values, samples, column_names, max_loc, max_val, ythresh = 3.0, xthresh = 1.5, dist_lim = 200.0, lawnmower = True)

        # Geneate data with distance truncation
        # dist_data, dist_sdata, d_props, d_propsy, ids, d_err_x, d_err_z = make_dist_dfs(values, samples, column_names, max_loc, max_val, ythresh = 3.0, xthresh = 1.5, dist_lim = 200.0)

        # dist_dfs.append(dist_data)
        # dist_samples_dfs.append(dist_sdata)
        # dist_props.append(d_props)
        # dist_propsy.append(d_propsy)
        # dist_ids.append(ids)
        # dist_err_x.append(d_err_x)
        # dist_err_z.append(d_err_z)

    print all_props
    print all_errx
    print all_errz

    # generate_stats(all_dfs, all_labels, ['distance', 'MSE', 'max_loc_error', 'max_val_error', 'max_value_info', 'info_regret'], 149, log_file_start + '_stats.txt')
    # generate_dist_stats(dist_dfs, labels, ['distance', 'MSE', 'max_loc_error', 'max_val_error', 'max_value_info', 'info_regret'], dist_ids, log_file_start + '_dist_stats.txt')

    # generate_histograms(all_sample_dfs, all_props, labels, title='All Iterations', figname=log_file_start, save_fig=False)
    generate_histograms(all_sample_dfs, all_props, labels, title='200$m$ Budget X Samples', figname=log_file_start, save_fig=False)
    generate_histograms(all_sample_dfs, all_propsy, labels, title='200$m$ Budget Y Samples', figname=log_file_start, save_fig=False)

    generate_histograms(all_sample_dfs, all_errx, labels, title='200$m$ Budget X Dist', figname=log_file_start, save_fig=False, ONLY_STATS = True)
    generate_histograms(all_sample_dfs, all_errz, labels, title='200$m$ Budget Z Dist', figname=log_file_start, save_fig=False, ONLY_STATS = True)

    # # def planning_iteration_plots(dfs, labels, param, title, end_time=149, d=20, plot_confidence=False, save_fig=False, fname='')
    # planning_iteration_plots(all_dfs, labels, 'MSE', 'Averaged MSE', 149, len(seeds), True, False, log_file_start+'_avg_mse.png')
    # planning_iteration_plots(all_dfs, labels, 'max_val_error', 'Val Error', 149, len(seeds), True, False, log_file_start+'_avg_rac.png')
    # planning_iteration_plots(all_dfs, labels, 'max_loc_error', 'Loc Error', 149, len(seeds), True, False, log_file_start+'_avg_ireg.png')

    # (dfs, sdfs, labels, param, title, dist_lim=150., granularity=10, d=20, plot_confidence=False, save_fig=False, fname=''):
    # distance_iteration_plots(dist_dfs, dist_ids, labels, 'MSE', 'Averaged MSE', 200., 100, len(seeds), True, False, '_avg_mse_dist.png' )
    # distance_iteration_plots(dist_dfs, dist_ids, labels, 'max_value_info', 'Reward Accumulation', 200., 100, len(seeds), True, False, '_avg_rac_dist.png' )
    # distance_iteration_plots(dist_dfs, dist_ids, labels, 'info_regret', 'Info Regret', 200., 100, len(seeds), True, False, '_avg_ireg_dist.png' )
    # distance_iteration_plots(dist_dfs, dist_ids, labels, 'max_loc_error', 'Loc Error', 200., 100, len(seeds), True, False, '_avg_locerr_dist.png' )


    plt.show()
