#!/usr/bin/env python
"""
Thomas Klijnsma
"""

########################################
# Imports
########################################

from numpy import corrcoef, var, std
import os
import os.path
import logging

import ROOT
from array import array

from differentials.plotting.canvas import c
import differentials.plotting as plotting
import differentials.core as core

from collections import namedtuple
Variation = namedtuple('Variation', ['values', 'parameters', 'is_central'])
Variation.is_central = False

class ScaleCorrelation(object):
    """docstring for ScaleCorrelation"""
    def __init__(self):
        self.variations = []
        self.do_wrt_central = False
        self.last_bin_is_overflow = False

        self.outdir = None
        self.default_outdir = 'out/scalecorrelations_{0}'.format(core.datestr())

    def get_outdir(self):
        if self.outdir is None:
            outdir = self.default_outdir
        else:
            outdir = self.outdir
        if not core.is_testmode() and not os.path.isdir(outdir):
            os.makedirs(outdir)
        return outdir

    def set_bin_boundaries(self, bin_boundaries, add_overflow=False):
        self.bin_boundaries = bin_boundaries
        logging.info('Bin boundaries set: {0}'.format(self.bin_boundaries))
        if add_overflow:
            self.n_bins = len(self.bin_boundaries)
            self.last_bin_is_overflow = True
            logging.info('Taking an overflow bin into account')
        else:
            self.n_bins = len(self.bin_boundaries)-1

    def add_variation(self, values, parameters, is_central=False):
        self.variations.append(Variation(values, parameters, is_central))

    def check_variation_consistency(self):
        # Check if passed variations make some sense
        assert len(self.variations) > 0
        for variation in self.variations:
            assert len(variation.values) == self.n_bins, (
                'Found len(variation.values) = {0} and self.n_bins = {1}, par_dict ='.format(len(variation.values), self.n_bins),
                variation.parameters,
                'bin_boundaries={0}'.format(self.bin_boundaries)
                )
        if self.do_wrt_central:
            assert len([v for v in self.variations if v.is_central]) == 1

    def get_bin_center(self, i):
        if self.do_wrt_central:
            central_variation = [v for v in self.variations if v.is_central][0]
            bin_center = central_variation.values[i]
        else:
            bin_center = sum(self.get_values(i))/len(self.variations)
        return bin_center

    def get_values(self, i):
        return [ variation.values[i] for variation in self.variations ]

    def get_correlation(self, i, j):
        values_x = self.get_values(i)
        values_y = self.get_values(j)
        corr = corrcoef( values_x, values_y )[0][1]
        return corr

    def calculate_correlation_matrix(self):
        self.check_variation_consistency()
        corrMatrix = [ [ 999 for j in xrange(self.n_bins) ] for i in xrange(self.n_bins) ]
        for i_row in xrange(self.n_bins):
            for i_col in xrange(self.n_bins):
                corrMatrix[i_row][i_col] = self.get_correlation(i_row, i_col)
        logging.debug(
            'Found the following correlation matrix:\n{0}'
            .format(
                '\n'.join(
                [ '  '.join([ '{0:+6.3f}'.format(corrMatrix[i_row][i_col]) for i_col in xrange(self.n_bins) ]) for i_row in xrange(self.n_bins) ]
                ))
            )
        return corrMatrix

    def calculate_errors(self):
        self.check_variation_consistency()
        errors = []
        for i in xrange(self.n_bins):
            values = self.get_values(i)
            e_min = abs( self.get_bin_center(i) - min(values) )
            e_max = abs( self.get_bin_center(i) - max(values) )
            width = self.bin_boundaries[i+1]-self.bin_boundaries[i]
            logging.info(
                'Multiplying errors in pb/GeV by bin width {0} to get errors in pb ({1}-{2})'
                .format(width, self.bin_boundaries[i], self.bin_boundaries[i+1])
                )
            e_min *= width
            e_max *= width
            errors.append([e_max, e_min])
        logging.debug('Found the following errors:\n{0}'.format('\n'.join([ '{0:+.5f} / {1:+.5f}'.format(l,r) for r,l in errors ])))
        return errors

    def write_correlation_matrix_to_file(self, tag=None):
        corrMatrix = self.calculate_correlation_matrix()
        outname = os.path.join( self.get_outdir(), 'corrMat' )
        if not(tag is None):
            outname += '_' + tag
        outname += '.txt'
        with open(outname, 'w') as out_fp:
            out_fp.write('# ' + core.gittag()+'\n')
            for i_row in xrange(self.n_bins):
                out_fp.write(
                    ' '.join([ '{0:+.4f}'.format(corrMatrix[i_row][i_col]) for i_col in xrange(self.n_bins) ])
                    + '\n'
                    )

    def write_errors_to_file(self, tag=None):
        errors = self.calculate_errors()
        outname = os.path.join( self.get_outdir(), 'errors' )
        if not(tag is None):
            outname += '_' + tag
        outname += '.txt'
        with open(outname, 'w') as out_fp:
            out_fp.write('# ' + core.gittag()+'\n')
            out_fp.write('# Uncertainties in pb (*not* pb/GeV)\n')
            out_fp.write('# Up        Down\n')
            for up, down in errors:
                out_fp.write('{0:+.8f} {1:+.8f}\n'.format( up, down ))


    def make_scatter_plots(self, subdir=None):
        for i_row in xrange(self.n_bins):
            print 'Processing correlations for bin {0}'.format(i_row)
            for i_col in xrange(self.n_bins):
                self.plot_scatter(i_row, i_col, subdir=subdir)

    def plot_scatter(self, i_bin, j_bin, subdir=None):
        self.check_variation_consistency()
        
        c.Clear()
        c.set_margins(RightMargin=0.1)

        values_x = self.get_values(i_bin)
        values_y = self.get_values(j_bin)
        corr = self.get_correlation(i_bin, j_bin)

        x_min = min(values_x) - 0.3*( max(values_x) - min(values_x) )
        x_max = max(values_x) + 0.3*( max(values_x) - min(values_x) )
        y_min = min(values_y) - 0.3*( max(values_y) - min(values_y) )
        y_max = max(values_y) + 0.3*( max(values_y) - min(values_y) )

        if self.last_bin_is_overflow and i_bin == self.n_bins-1:
            x_title = 'pT > {0:.1f}'.format(self.bin_boundaries[-1])
        else:
            x_title = '{0:.1f} < pT < {1:.1f}'.format(self.bin_boundaries[i_bin], self.bin_boundaries[i_bin+1])

        if self.last_bin_is_overflow and j_bin == self.n_bins-1:
            y_title = 'pT > {0:.1f}'.format(self.bin_boundaries[-1])
        else:
            y_title = '{0:.1f} < pT < {1:.1f}'.format(self.bin_boundaries[j_bin], self.bin_boundaries[j_bin+1])

        base = plotting.pywrappers.Base(
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            x_title=x_title, y_title=y_title
            )
        base.Draw()

        Tg = ROOT.TGraph( self.n_bins, array('d', values_x), array('d', values_y) )
        ROOT.SetOwnership( Tg, False )
        Tg.SetMarkerColor(9)
        Tg.SetMarkerStyle(8)
        Tg.SetMarkerSize(0.8)
        Tg.Draw('PSAME')

        x_mean = self.get_bin_center(i_bin)
        x_mean_line = ROOT.TLine(x_mean, y_min, x_mean, y_max)
        ROOT.SetOwnership(x_mean_line, False)
        x_mean_line.Draw()

        y_mean = self.get_bin_center(j_bin)
        y_mean_line = ROOT.TLine(x_min, y_mean, x_max, y_mean)
        ROOT.SetOwnership(y_mean_line, False)
        y_mean_line.Draw()

        slope  = corr * std(values_y)/std(values_x)
        offset = y_mean - slope * x_mean
        fnCorrLine = lambda x: slope*x + offset
        corr_line = ROOT.TLine( x_min, fnCorrLine(x_min), x_max, fnCorrLine(x_max) )
        ROOT.SetOwnership( corr_line, False )
        corr_line.SetLineWidth(2)
        corr_line.SetLineColor(2)
        corr_line.Draw()

        l = plotting.pywrappers.Latex(
            lambda c: c.GetLeftMargin() + 0.02,
            lambda c: 1.0 - c.GetTopMargin() - 0.01,
            '#rho = {0:.2f}'.format(corr)
            )
        l.SetNDC()
        l.SetTextSize(0.06)
        l.SetTextAlign(13)
        l.Draw()

        if subdir is None:
            subdir = 'Bin{0}'.format(i_bin)
        else:
            subdir = '{0}/Bin{1}'.format(subdir, i_bin)
        outname = os.path.join(subdir, 'Correlation_Bin{0}_Bin{1}'.format(i_bin, j_bin))
        c.save(outname)


    def plot_correlation_matrix(self, tag=None):
        corrMat = self.calculate_correlation_matrix()

        c.Clear()
        c.set_margins(
            LeftMargin   = 0.21,
            RightMargin  = 0.12,
            TopMargin    = 0.12,
            BottomMargin = 0.19,
            )

        T = ROOT.TH2D(
            'corrMat', '#scale[0.85]{Correlation between p_{T} bins}',
            self.n_bins, 0., self.n_bins,
            self.n_bins, 0., self.n_bins
            )
        ROOT.SetOwnership( T, False )
        T.SetContour(100)
        for i_row in xrange(self.n_bins):
            for i_col in xrange(self.n_bins):
                T.SetBinContent( i_col+1, i_row+1, corrMat[i_row][i_col] )
        T.GetZaxis().SetRangeUser(-1.0,1.0)

        toString = lambda number: str(int(number)) if number.is_integer() else '{0:.1f}'.format(number)
        for i in xrange(self.n_bins):
            if self.last_bin_is_overflow and i == self.n_bins-1:
                label = toString(self.bin_boundaries[i]) + '-#infty'
            else:
                label = '{0}-{1}'.format(
                    toString(self.bin_boundaries[i]), toString(self.bin_boundaries[i+1])
                    )
            if self.n_bins < 20 or i % int(0.1*self.n_bins) == 0:
                T.GetXaxis().SetBinLabel(i+1, label)
                T.GetYaxis().SetBinLabel(i+1, label)

        n_stops = 3
        stops  = [ 0.0, 0.5, 1.0 ]
        reds   = [ 0.0, 1.0, 1.0 ]
        blues  = [ 1.0, 1.0, 0.0 ]
        greens = [ 0.0, 1.0, 0.0 ]

        ROOT.TColor.CreateGradientColorTable(
            n_stops,
            array('d', stops ),
            array('d', reds ),
            array('d', greens ),
            array('d', blues ),
            255 )

        T.GetXaxis().SetTitle( 'p_{T} [GeV]' )
        T.GetXaxis().SetTitleOffset( 1.7 )
        T.GetXaxis().SetTitleSize(0.055)

        T.GetYaxis().SetTitle( 'p_{T} [GeV]' )
        T.GetYaxis().SetTitleOffset( 1.65 )
        T.GetYaxis().SetTitleSize(0.055)

        T.GetXaxis().SetLabelSize(0.055)
        T.GetYaxis().SetLabelSize(0.055)

        ROOT.gStyle.SetHistMinimumZero() # To draw the "0", otherwise ROOT leaves it empty
        ROOT.gStyle.SetPaintTextFormat('1.2g')

        T.SetMarkerSize(1.35)
        
        if self.n_bins < 20:
            T.Draw('COLZ TEXT')
        else:
            T.Draw('COLZ')

        c.cd()
        c.Update()

        outname = 'corrMat'
        if not(tag is None):
            outname += '_' + tag
        # SaveC(outname, asPNG=True)
        c.save(outname)