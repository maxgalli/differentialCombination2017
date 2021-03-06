from OptionHandler import flag_as_option, flag_as_parser_options

import LatestPaths, LatestBinning
import sys

import differentials
import differentialutils

from time import strftime
datestr = strftime( '%b%d' )

import os, logging
from os.path import *
from math import sqrt

import ROOT
from array import array

#____________________________________________________________________
# Total XS

@flag_as_option
def totalXS_t2ws(args):
    card = LatestPaths.card.inclusive[differentialutils.get_decay_channel_tag(args)]
    t2ws = differentials.combine.t2ws.T2WS(card)
    t2ws.add_map('.*/.*sideAcceptance.*:r[1.0,0.1,2.0]')
    t2ws.add_map('.*/smH_INC_INC:r[1.0,0.1,2.0]')
    t2ws.run()

def totalXS_scan_config(args):
    if args.asimov:
        logging.warning('This is probably not what I want')
        return

    config = differentials.combine.combine.CombineConfig(args)
    config.onBatch       = True
    config.queue         = 'short.q'
    config.nPoints       = 55
    config.nPointsPerJob = config.nPoints

    r_ranges = [ 0.1, 2.0 ]
    config.POIs = [ 'r' ]
    config.PhysicsModelParameterRanges = [
        'r={0},{1}'.format( r_ranges[0], r_ranges[1] ),
        ]
    config.subDirectory = 'out/Scan_{0}_totalXS'.format(datestr)
    return config

@flag_as_option
def totalXS_scan(args):
    config = totalXS_scan_config(args)

    decay_channel = differentialutils.get_decay_channel_tag(args)
    config.datacard = LatestPaths.ws.totalXS[decay_channel]
    config.tags.append(decay_channel)

    config.make_unique_directory()

    postfit = differentials.combine.combine.CombinePostfit(config)
    postfit.run()
    postfit_file = postfit.get_output()

    # Stat+syst scan (regular)
    scan = differentials.combine.combine.CombineScanFromPostFit(config)
    scan.run(postfit_file)

    # Stat-only scan
    scan_stat_only = differentials.combine.combine.CombineScanFromPostFit(config)
    scan_stat_only.subDirectory += '_statonly'
    scan_stat_only.freezeNuisances.append('rgx{.*}')
    scan_stat_only.run(postfit_file)


@flag_as_option
def totalXS_nuispars(args):
    postfit = join(
        LatestPaths.scan.totalXS.combination,
        'postfit_and_fastscan',
        'higgsCombine_POSTFIT_combination_inclusive_Mar19_multiSignalModel.MultiDimFit.mH125.root'
        )
    ws = differentials.core.get_ws(postfit)
    status = ws.loadSnapshot('MultiDimFit')
    nuispars = [ 'CMS_eff_e', 'CMS_eff_m', 'CMS_hgg_JEC', 'CMS_hgg_JER', 'CMS_hgg_LooseMvaSF', 'CMS_hgg_PreselSF', 'CMS_hgg_SigmaEOverEShift', 'CMS_hgg_TriggerWeight', 'CMS_hgg_electronVetoSF', 'CMS_hgg_phoIdMva', 'CMS_hzz2e2mu_Zjets', 'CMS_hzz4e_Zjets', 'CMS_hzz4mu_Zjets', 'CMS_zjets_bkgdcompo', 'QCDscale_VV', 'QCDscale_ggVV', 'kfactor_ggzz', 'lumi_13TeV', 'norm_nonResH', 'pdf_gg', 'pdf_qqbar', 'CMS_hgg_nuisance_LowR9EB_13TeVscale', 'CMS_zz4l_n_sig_3_8', 'CMS_zz4l_mean_m_sig', 'CMS_hgg_nuisance_Gain1EB_13TeVscale', 'CMS_hgg_nuisance_LightColl_13TeVscale', 'CMS_hgg_nuisance_Gain6EB_13TeVscale', 'CMS_hgg_nuisance_HighR9EB_13TeVsmear', 'CMS_hgg_nuisance_LowR9EB_13TeVsmear', 'CMS_zz4l_n_sig_2_8', 'CMS_zz4l_mean_e_sig', 'CMS_zz4l_sigma_m_sig', 'CMS_hgg_nuisance_deltafracright', 'CMS_hgg_nuisance_Absolute_13TeVscale', 'CMS_hgg_nuisance_MaterialForward_scale', 'CMS_hgg_nuisance_NonLinearity_13TeVscale', 'CMS_hgg_nuisance_MaterialCentral_scale', 'CMS_hgg_nuisance_LowR9EE_13TeVsmear', 'CMS_zz4l_sigma_e_sig', 'CMS_hgg_nuisance_Geant4_13TeVscale', 'CMS_hgg_nuisance_HighR9EE_13TeVscale', 'CMS_zz4l_n_sig_1_8', 'CMS_hgg_nuisance_HighR9EE_13TeVsmear', 'CMS_hgg_nuisance_LowR9EE_13TeVscale', 'CMS_hgg_nuisance_HighR9EB_13TeVscale' ]

    d = []
    maxname = max(map(len, nuispars))
    for nuispar in nuispars:
        val = ws.var(nuispar).getVal()
        print '{0:{width}}: {1}'.format(nuispar, val, width=maxname)
        d.append((nuispar, val))
    d.sort(key=lambda tup: -abs(tup[1]))

    c = differentials.plotting.canvas.c
    c.Clear()

    ROOT.gStyle.SetBarWidth(0.5)

    g = ROOT.TGraph(
        len(d),
        array('d', range(len(d))),
        array('d', [t[1] for t in d] )
        )
    g.Draw('AB')
    g.SetFillColor(40)

    print 'Nr. of nuispars:'
    print len(nuispars)

    g.SetTitle('Nuisance parameters for #sigma_{tot} at best fit')
    g.GetXaxis().SetTitle('Nuis. par. index')
    g.GetYaxis().SetTitle('Value')

    c.save('totalXS_nuispars')

    print d[:5]



@flag_as_option
def totalXS_plot(args):
    scans = LatestPaths.scan.totalXS
    scans_statonly = LatestPaths.scan.totalXS.statonly

    hgg = differentials.scans.Scan('r', scandir=scans.hgg)
    hgg.color = differentials.core.safe_colors.red
    hgg.draw_style = 'repr_smooth_line'
    hgg.title = differentials.core.standard_titles['hgg']
    hgg.no_bestfit_line = True

    # hgg_statonly = differentials.scans.Scan('r', scandir=scans_statonly.hgg)
    # hgg_statonly.color = differentials.core.safe_colors.red
    # hgg_statonly.draw_style = 'repr_smooth_line'
    # hgg_statonly.line_style = 2
    
    hzz = differentials.scans.Scan('r', scandir=scans.hzz)
    hzz.color = differentials.core.safe_colors.blue
    hzz.draw_style = 'repr_smooth_line'
    hzz.title = differentials.core.standard_titles['hzz']
    hzz.no_bestfit_line = True
    
    # hzz_statonly = differentials.scans.Scan('r', scandir=scans_statonly.hzz)
    # hzz_statonly.color = differentials.core.safe_colors.blue
    # hzz_statonly.draw_style = 'repr_smooth_line'
    # hzz_statonly.line_style = 2
    
    combination = differentials.scans.Scan('r', scandir=scans.combination)
    combination.color = 1
    combination.draw_style = 'repr_smooth_line'
    combination.title = 'Combination'
    
    combination_statonly = differentials.scans.Scan('r', scandir=scans_statonly.combination)
    combination_statonly.color = 11
    combination_statonly.draw_style = 'repr_smooth_line'
    combination_statonly.line_style = 2
    combination_statonly.title = 'Stat uncertainty'
    combination_statonly.no_bestfit_line = True

    for scan in [
        hgg,
        # hgg_statonly,
        hzz,
        # hzz_statonly,
        combination,
        combination_statonly,
        ]:
        scan.read(keep_chain=True)
        # scan.multiply_x_by_constant(LatestBinning.YR4_totalXS)
        scan.create_uncertainties()

    plot = differentials.plotting.plots.MultiScanPlot('scans_totalXS')

    # plot.x_min = 0.0
    plot.x_min = 0.4 * LatestBinning.YR4_totalXS
    plot.x_max = 1.6 * LatestBinning.YR4_totalXS
    plot.y_max = 5.5
    plot.x_title = '#sigma_{tot} (pb)'

    # plot.add_scan(hgg)
    # plot.add_scan(hzz)
    # plot.add_scan(combination)
    # plot.add_scan(combination_statonly)

    for scan in [
            hgg, hzz, combination, combination_statonly
            ]:
        spline = scan.to_spline(x_min = 0.5, x_max = 1.7)
        graph = spline.to_graph(nx=1500)
        graph.multiply_x_by_constant(LatestBinning.YR4_totalXS)
        graph.raise_to_zero()
        graph.style().color = scan.color
        graph.title = scan.title
        # graph.line_width = 5
        # graph.line_style = 2
        # if scan is combination:
        #     graph.draw_bestfit = True
        plot.manual_graphs.append(graph)

    plot.draw()

    plot.leg.SetNColumns(1)
    plot.leg.set(
        x1 = lambda c: c.GetLeftMargin() + 0.0,
        x2 = lambda c: c.GetLeftMargin() + 0.79,
        # x1 = lambda c: c.GetLeftMargin() + 0.04,
        # # x2 = lambda c: c.GetLeftMargin() + 0.35,
        # x2 = lambda c: 1.-c.GetRightMargin() - 0.15,
        y1 = lambda c: 1-c.GetTopMargin() - 0.25,
        y2 = lambda c: 1-c.GetTopMargin() - 0.01,
        )

    xs              = combination.unc.x_min
    xs_err_full     = combination.unc.symm_error
    xs_err_statonly = combination_statonly.unc.symm_error
    xs_err_systonly = sqrt(xs_err_full**2 -xs_err_statonly**2)
    xs              *= LatestBinning.YR4_totalXS
    xs_err_full     *= LatestBinning.YR4_totalXS
    xs_err_statonly *= LatestBinning.YR4_totalXS
    xs_err_systonly *= LatestBinning.YR4_totalXS

    bestfitline = differentials.plotting.pywrappers.Graph(
        'sm', 'SM',
        [xs, xs], [0.0, plot.y_cutoff]
        )
    bestfitline.style().color = 1
    bestfitline.line_width = 1
    bestfitline.Draw('repr_basic_line')

    sm_legend_dummy = ROOT.TGraphErrors(
        1,
        array('f', [-999.]),
        array('f', [-999.]),
        array('f', [1.0]),
        array('f', [1.0])
        )
    sm_legend_dummy.SetFillColorAlpha(differentials.core.safe_colors.green, 0.2)
    sm_legend_dummy.SetLineColor(differentials.core.safe_colors.green)
    sm_legend_dummy.SetLineWidth(2)
    ROOT.SetOwnership(sm_legend_dummy, False)
    sm_legend_dummy.Draw('SAMEP5')
    sm_legend_dummy.SetName('sm_legend_dummy')
    plot.leg.AddEntry(sm_legend_dummy.GetName(), '#sigma_{SM} from CYRM-2017-002', 'lf')

    smbox = differentials.plotting.pywrappers.Box(
        LatestBinning.YR4_totalXS - LatestBinning.smH_unc_inclusive,
        0.0,
        LatestBinning.YR4_totalXS + LatestBinning.smH_unc_inclusive,
        plot.y_cutoff
        )
    smbox.color = differentials.core.safe_colors.green
    smbox.Draw()

    smline = differentials.plotting.pywrappers.Graph(
        'sm', 'SM',
        [LatestBinning.YR4_totalXS, LatestBinning.YR4_totalXS], [0.0, plot.y_cutoff]
        )
    smline.style().color = differentials.core.safe_colors.green
    # smline._legend = plot.leg
    smline.line_width = 1
    smline.Draw('repr_basic_line')

    l = differentials.plotting.pywrappers.Latex(
        differentials.plotting.canvas.c.GetLeftMargin() + 0.045,
        1-differentials.plotting.canvas.c.GetTopMargin() - 0.26,
        '#sigma_{{tot}} = {0:.1f}  #pm{1:.1f} (stat) #pm{2:.1f} (syst)  pb'.format(
            # xBestfit, 0.5*(abs(left_stat)+abs(right_stat)), 0.5*(abs(left_syst)+abs(right_syst))
            xs, xs_err_statonly, xs_err_systonly
            )
        )
    l.SetNDC()
    l.SetTextAlign(13)
    l.SetTextColor(1)
    l.SetTextSize(0.040)
    l.SetTextFont(42)
    l.Draw()

    # l2 = differentials.plotting.pywrappers.Latex(
    #     lambda c: c.GetLeftMargin() + 0.04,
    #     lambda c: c.GetBottomMargin() + 0.045,
    #     '#sigma_{SM} from CYRM-2017-002'
    #     )
    # l2.SetNDC()
    # l2.SetTextAlign(11)
    # l2.SetTextFont(42) 
    # l2.SetTextSize(0.038)
    # l2.Draw()

    differentials.plotting.canvas.c.resize_temporarily(800,800)

    plot.base.GetYaxis().SetTitleOffset(0.75)
    
    plot.wrapup()

    logging.info(
        'Numerical values:'
        '\nhgg:  {0} +- {1}'
        '\nhzz:  {2} +- {3}'
        '\ncomb: {4} +- {5}'
        .format(
            hgg.unc.x_min, hgg.unc.symm_error,
            hzz.unc.x_min, hzz.unc.symm_error,
            combination.unc.x_min, combination.unc.symm_error,
            )
        )


#____________________________________________________________________
# Ratio of BRs

@flag_as_option
def ratioBR_t2ws(args):
    # card = LatestPaths.card.pth_smH.combination

    # This is for inclusive
    card = LatestPaths.card.inclusive.combination
    t2ws = differentials.combine.t2ws.T2WS(card, 'physicsModels/ExtendedMultiSignalModel.py')
    t2ws.tags.append('ratioOfBRs')
    t2ws.add_map('hzz.*/.*smH_INC_INC:hzz_BRmodifier')
    t2ws.add_map('hgg.*/.*sideAcceptance:hgg_BRmodifier')

    t2ws.extra_options.append('--PO \'get_splines\'')
    t2ws.add_variable('hgg_BRmodifier', 1.0, -2.0, 4.0, is_POI=True)
    t2ws.add_variable('ratio_BR_hgg_hzz', 0.086, 0.0, 0.5, is_POI=True)

    hzz_modifier_expr = (
        'expr::hzz_BRmodifier("@0*(@1/@2)/@3",'
        'hgg_BRmodifier,'
        '#spline_hgg,' # Will be replaced by model
        '#spline_hzz,' # Will be replaced by model
        'ratio_BR_hgg_hzz'
        ')'
        )
    t2ws.add_expr(hzz_modifier_expr)

    t2ws.run()

@flag_as_option
def ratioBR_scan(args):
    if args.asimov:
        logging.warning('This is probably not what I want')
        return

    config = differentials.combine.combine.CombineConfig(args)
    config.onBatch       = True
    config.queue         = 'short.q'
    config.nPoints       = 55
    config.nPointsPerJob = config.nPoints

    r_ranges = [ 0.06, 0.16 ]
    config.POIs = [ 'ratio_BR_hgg_hzz' ]
    config.PhysicsModelParameterRanges = [
        'ratio_BR_hgg_hzz={0},{1}'.format( r_ranges[0], r_ranges[1] ),
        ]
    config.subDirectory = 'out/Scan_{0}_ratioOfBRs'.format(datestr)

    config.datacard = LatestPaths.ws.ratioOfBRs

    config.make_unique_directory()

    postfit = differentials.combine.combine.CombinePostfit(config)
    postfit.run()
    postfit_file = postfit.get_output()

    # Stat+syst scan (regular)
    scan = differentials.combine.combine.CombineScanFromPostFit(config)
    scan.run(postfit_file)

    # Stat-only scan
    scan_stat_only = differentials.combine.combine.CombineScanFromPostFit(config)
    scan_stat_only.subDirectory += '_statonly'
    scan_stat_only.freezeNuisances.append('rgx{.*}')
    scan_stat_only.run(postfit_file)


@flag_as_option
def ratioBR_plot(args):
    plot = differentials.plotting.plots.MultiScanPlot('scans_ratioOfBRs')

    plot.x_min = 0.3 * LatestBinning.SM_ratio_of_BRs
    plot.x_max = 1.7 * LatestBinning.SM_ratio_of_BRs
    plot.y_max = 5.5
    plot.x_title = '#frac{{{2}({0})}}{{{2}({1})}}'.format(
        differentials.core.standard_titles['hgg'],
        differentials.core.standard_titles['hzz'],
        differentials.core.standard_titles['BR']
        )

    ratioOfBRs_statonly = differentials.scans.Scan('ratio_BR_hgg_hzz', scandir=LatestPaths.scan.ratioOfBRs_statonly)
    ratioOfBRs_statonly.read(keep_chain=True)
    ratioOfBRs_statonly.color = 11
    ratioOfBRs_statonly.draw_style = 'repr_smooth_line'
    ratioOfBRs_statonly.title = 'Stat uncertainty'
    ratioOfBRs_statonly.create_uncertainties()
    # plot.add_scan(ratioOfBRs_statonly)

    ratioOfBRs = differentials.scans.Scan('ratio_BR_hgg_hzz', scandir=LatestPaths.scan.ratioOfBRs)
    ratioOfBRs.read(keep_chain=True)
    ratioOfBRs.color = 1
    # ratioOfBRs.draw_style = 'repr_smooth_line'
    ratioOfBRs.draw_style = 'repr_basic_line'
    ratioOfBRs.title = 'Combination'
    ratioOfBRs.create_uncertainties()
    # plot.add_scan(ratioOfBRs)

    for scan in [
            ratioOfBRs_statonly, ratioOfBRs
            ]:
        spline = scan.to_spline(x_min = 0.06, x_max = 0.145)
        graph = spline.to_graph(nx=1500)
        # graph.multiply_x_by_constant(LatestBinning.YR4_totalXS)
        graph.style().color = scan.color
        graph.title = scan.title
        # graph.line_width = 5
        # graph.line_style = 2
        if scan is ratioOfBRs:
            graph.draw_bestfit = True
        plot.manual_graphs.append(graph)

    plot.draw()

    plot.base.GetXaxis().SetTitleSize(0.043)
    plot.base.GetXaxis().SetTitleOffset(1.4)
    plot.base.GetYaxis().SetTitleOffset(0.75)

    plot.leg.SetNColumns(1)
    plot.leg.set(
        x1 = lambda c: c.GetLeftMargin() + 0.0,
        x2 = lambda c: c.GetLeftMargin() + 0.81,
        y1 = lambda c: 1-c.GetTopMargin() - 0.22,
        y2 = lambda c: 1-c.GetTopMargin() - 0.02,
        )

    #____________________________________________________________________
    # SM line

    smUncBox = differentials.plotting.pywrappers.Box(
        LatestBinning.SM_ratio_of_BRs - abs(LatestBinning.SM_ratio_of_BRs_unc_down),
        0.,
        LatestBinning.SM_ratio_of_BRs + abs(LatestBinning.SM_ratio_of_BRs_unc_up),
        plot.y_cutoff
        )
    smUncBox.color = differentials.core.safe_colors.green
    smUncBox.Draw()

    smline = differentials.plotting.pywrappers.Graph(
        'sm', 'title',
        [LatestBinning.SM_ratio_of_BRs, LatestBinning.SM_ratio_of_BRs], [0.0, plot.y_cutoff]
        )
    smline.style().color = differentials.core.safe_colors.green
    smline.line_width = 2
    smline.Draw('repr_basic_line')

    # Dummy to get the legend entry right
    sm_legend_title = '#frac{{{BR}({0})}}{{{BR}({1})}} from CYRM-2017-002'.format(
        differentials.core.standard_titles['hgg'],
        differentials.core.standard_titles['hzz'],
        BR = differentials.core.standard_titles['BR']
        )
    sm_legend_dummy = ROOT.TGraphErrors(
        1,
        array('f', [-999.]),
        array('f', [-999.]),
        array('f', [1.0]),
        array('f', [1.0])
        )
    sm_legend_dummy.SetFillColorAlpha(differentials.core.safe_colors.green, 0.2)
    sm_legend_dummy.SetLineColor(differentials.core.safe_colors.green)
    sm_legend_dummy.SetLineWidth(2)
    ROOT.SetOwnership(sm_legend_dummy, False)
    sm_legend_dummy.Draw('SAMEP5')
    sm_legend_dummy.SetName('sm_legend_dummy')
    plot.leg.AddEntry(sm_legend_dummy.GetName(), sm_legend_title, 'lf')
    #____________________________________________________________________

    xs = ratioOfBRs.unc.x_min
    xs_err_full = ratioOfBRs.unc.symm_error
    xs_err_statonly = ratioOfBRs_statonly.unc.symm_error
    xs_err_systonly = sqrt(xs_err_full**2 -xs_err_statonly**2)

    l = differentials.plotting.pywrappers.Latex(
        differentials.plotting.canvas.c.GetLeftMargin() + 0.045,
        1-differentials.plotting.canvas.c.GetTopMargin() - 0.24,
        '{0} = {1:.3f}  #pm{2:.3f} (stat) #pm{3:.3f} (syst)'.format(
            plot.x_title,
            xs, xs_err_statonly, xs_err_systonly
            )
        )
    l.SetNDC()
    l.SetTextAlign(13)
    l.SetTextColor(1)
    l.SetTextSize(0.035)
    l.SetTextFont(42)
    l.Draw()

    differentials.plotting.canvas.c.resize_temporarily(800,800)
    plot.wrapup()





