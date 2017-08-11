#!/usr/bin/env python
"""
Thomas Klijnsma
"""

########################################
# Imports
########################################

import os, itertools, operator, re, argparse, sys, random
from math import isnan, isinf
from os.path import *
from glob import glob
from copy import deepcopy

sys.path.append('src')
import Commands
import PhysicsCommands
import OneOfCommands
import TheoryCommands
import CorrelationMatrices
import MergeHGGWDatacards
import TheoryFileInterface
from Container import Container
from Parametrization import Parametrization, WSParametrization

from time import strftime
datestr = strftime( '%b%d' )

import ROOT
from TheoryCommands import c
from TheoryCommands import SaveC
from TheoryCommands import GetPlotBase
from TheoryCommands import SetCMargins


########################################
# Main
########################################

def AppendParserOptions( parser ):

    parser.add_argument( '--topCommands', default=False )
    class CustomAction(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            # Only 1 argument allowed (this is basically the "store_true" action)
            super(CustomAction, self).__init__(option_strings, dest, nargs=0, **kwargs)
        def __call__(self, parser, namespace, values, option_string=None):
            # Make sure the parser knows a combineCommand was entered
            setattr( namespace, 'topCommands', True )
            setattr( namespace, self.dest, True )
            # super(FooAction, self).__call__( parser, namespace, values, option_string=None )
            # setattr( namespace, self.dest, values )

    parser.add_argument( '--createDerivedTheoryFiles_Top',                  action=CustomAction )
    parser.add_argument( '--CorrelationMatrices_Top',                       action=CustomAction )
    parser.add_argument( '--couplingT2WS_Top',                              action=CustomAction )
    parser.add_argument( '--couplingBestfit_Top',                           action=CustomAction )
    parser.add_argument( '--coupling2Dplot_Top',                            action=CustomAction )
    parser.add_argument( '--checkWSParametrization_Top',                    action=CustomAction )


########################################
# Methods
########################################    

def main( args ):

    # expBinBoundaries = [ 0., 15., 30., 45., 85., 125. ]
    expBinBoundaries = [ 0., 15., 30., 45., 85., 125., 200., 350. ]
    print 'Hardcoded binBoundaries for Top:'
    print expBinBoundaries
    print ''

    LATESTDATACARD_Top            = 'suppliedInput/combinedCard_Jul26.txt'

    LATESTWORKSPACE_Top           = 'workspaces_Aug11/combinedCard_Jul26_CouplingModel_Top_withTheoryUncertainties.root'

    LATESTTHEORYDIR_Top           = 'derivedTheoryFiles_Aug11_Top'
    LATESTCORRELATIONMATRIX_Top   = 'plots_CorrelationMatrices_Aug11_Top/corrMat_exp.txt'
    LATESTTHEORYUNCERTAINTIES_Top = 'plots_CorrelationMatrices_Aug11_Top/errors_for_corrMat_exp.txt'

    TheoryCommands.SetPlotDir( 'plots_{0}_Top'.format(datestr) )


    #____________________________________________________________________
    if args.createDerivedTheoryFiles_Top:
        TheoryFileInterface.CreateDerivedTheoryFiles_Top(
            # verbose = True,
            )


    #____________________________________________________________________
    if args.CorrelationMatrices_Top:

        CorrelationMatrices.SetPlotDir( 'plots_CorrelationMatrices_{0}_Top'.format(datestr) )

        variationFiles = TheoryFileInterface.FileFinder(
            directory = LATESTTHEORYDIR_Top,
            ct = 1.0, cg = 1.0, cb = 1.0
            )

        variations = [
            TheoryFileInterface.ReadDerivedTheoryFile( variationFile ) for variationFile in variationFiles ]

        CorrelationMatrices.GetCorrelationMatrix(
            variations,
            makeScatterPlots          = False,
            makeCorrelationMatrixPlot = True,
            outname                   = 'corrMat_theory',
            verbose                   = True,
            )

        variations_expbinning = deepcopy(variations)
        for variation in variations_expbinning:
            TheoryCommands.RebinDerivedTheoryContainer( variation, expBinBoundaries )

        CorrelationMatrices.GetCorrelationMatrix(
            variations_expbinning,
            makeScatterPlots          = True,
            makeCorrelationMatrixPlot = True,
            outname                   = 'corrMat_exp',
            verbose                   = True,
            )

    #____________________________________________________________________
    if args.couplingT2WS_Top:

        INCLUDE_THEORY_UNCERTAINTIES = True
        # INCLUDE_THEORY_UNCERTAINTIES = False

        # datacard = 'suppliedInput/combinedCard_Jul26.txt'
        datacard = LATESTDATACARD_Top

        TheoryFileInterface.SetFileFinderDir( LATESTTHEORYDIR_Top )

        extraOptions = [
            '--PO verbose=2',
            '--PO \'higgsMassRange=123,127\'',
            '--PO linearTerms=False',
            ]

        extraOptions.append(
            '--PO SM=[ct=1,cg=0,file={0}]'.format(
                TheoryFileInterface.FileFinder( ct=1, cg=1, cb=1, muR=1, muF=1, Q=1, expectOneFile=True )
                )
            )

        
        theoryFiles = TheoryFileInterface.FileFinder(
            ct='*', cg='*', muR=1, muF=1, Q=1, filter='cb'
            )
        possibleTheories = []
        for theoryFile in theoryFiles:
            ct = Commands.ConvertStrToFloat( re.search( r'ct_([\dmp]+)', theoryFile ).group(1) )
            cg = Commands.ConvertStrToFloat( re.search( r'cg_([\dmp]+)', theoryFile ).group(1) )
            possibleTheories.append(
                '--PO theory=[ct={0},cg={1},file={2}]'.format(
                    ct, cg, theoryFile
                    )                
                )
        extraOptions.extend(possibleTheories)


        suffix = 'Top'
        if INCLUDE_THEORY_UNCERTAINTIES:
            extraOptions.append(
                '--PO correlationMatrix={0}'.format(LATESTCORRELATIONMATRIX_Top) )
            extraOptions.append(
                '--PO theoryUncertainties={0}'.format(LATESTTHEORYUNCERTAINTIES_Top) )
            suffix += '_withTheoryUncertainties'


        # Scale these bins with 1.0 regardless of parametrization
        extraOptions.append(
            '--PO skipBins=GT350'
            )

        Commands.BasicT2WSwithModel(
            datacard,
            'CouplingModel.py',
            suffix = suffix,
            extraOptions = extraOptions,
            )


    #____________________________________________________________________
    if args.couplingBestfit_Top:

        doFastscan = True
        if args.notFastscan: doFastscan = False

        ASIMOV = False
        # ASIMOV = True

        datacard = LATESTWORKSPACE_Top

        ct_ranges = [ -5., 10. ]
        cg_ranges = [ -1., 1. ]

        jobDirectory = 'Scan_couplings_{0}'.format( datestr )
        if ASIMOV: jobDirectory += '_asimov'
        jobDirectory = Commands.AppendNumberToDirNameUntilItDoesNotExistAnymore( jobDirectory )


        if doFastscan:
            nPoints = 6400
            nPointsPerJob = 100
            queue = 'short.q'
        else:
            nPoints = 6400
            nPointsPerJob = 50
            queue = 'long.q'

        Commands.MultiDimCombineTool(
            datacard,
            nPoints       = nPoints,
            nPointsPerJob = nPointsPerJob,
            queue         = queue,
            notOnBatch    = False,
            jobDirectory  = jobDirectory,
            fastscan      = doFastscan,
            asimov        = ASIMOV,
            extraOptions  = [
                # '--importanceSampling={0}:couplingScan'.format( abspath('scanTH2D_Jun01.root') ),
                '-P ct -P cg',
                '--setPhysicsModelParameters ct=1.0,cg=1.0',
                '--setPhysicsModelParameterRanges ct={0},{1}:cg={2},{3}'.format(
                    ct_ranges[0], ct_ranges[1], cg_ranges[0], cg_ranges[1] ),
                '--saveSpecifiedFunc {0}'.format(','.join(
                    Commands.ListSet( datacard, 'yieldParameters' ) + [ i for i in Commands.ListSet( datacard, 'ModelConfig_NuisParams' ) if i.startswith('theoryUnc') ]  ) ),
                '--squareDistPoiStep',
                ]
            )


    #____________________________________________________________________
    if args.coupling2Dplot_Top:

        datacard = LATESTWORKSPACE_Top
        
        scandir  = 'Scan_couplings_Aug11'

        res = TheoryCommands.PlotCouplingScan2D(
            datacard,
            glob( '{0}/*.root'.format(scandir) ),
            xCoupling = 'ct',
            yCoupling = 'cg',
            )

        print '\nBest fit:'
        print res.xCoupling, '=', res.xBestfit
        print res.yCoupling, '=', res.yBestfit


    #____________________________________________________________________
    if args.checkWSParametrization_Top:

        plotCombination = False

        # DrawExperimentalBinLines = False
        DrawExperimentalBinLines = True

        # wsToCheck = 'workspaces_Aug11/combinedCard_Jul26_CouplingModel_Top_withTheoryUncertainties.root'
        wsToCheck = LATESTWORKSPACE_Top
        wsParametrization = WSParametrization( wsToCheck )

        theoryDir = LATESTTHEORYDIR_Top
        TheoryFileInterface.SetFileFinderDir( theoryDir )
        topDerivedTheoryFiles = TheoryFileInterface.FileFinder(
            ct='*', cg='*', muR=1, muF=1, Q=1, filter='cb'
            )

        containers = []
        colorCycle = itertools.cycle( range(2,5) + range(6,10) + range(40,50) + [ 30, 32, 33, 35, 38, 39 ] )
        for topDerivedTheoryFile in topDerivedTheoryFiles:
            color = next(colorCycle)

            print topDerivedTheoryFile

            container = TheoryFileInterface.ReadDerivedTheoryFile( topDerivedTheoryFile )
            container.name = 'ct_{0}_cg_{1}'.format(
                Commands.ConvertFloatToStr( container.ct ),
                Commands.ConvertFloatToStr( container.cg ),
                )

            container.Tg_theory = TheoryFileInterface.ReadDerivedTheoryFileToTGraph( topDerivedTheoryFile, name = container.name )
            container.Tg_theory.SetLineWidth(2)
            container.Tg_theory.SetLineColor(color)
            container.Tg_theory.SetMarkerColor(color)
            container.Tg_theory.SetLineStyle(2)
            container.Tg_theory.SetMarkerStyle(8)
            container.Tg_theory.SetMarkerSize(0.8)

            container.Tg_parametrization = wsParametrization.GetOutputContainer(
                ct = container.ct , cg = container.cg,
                returnWhat='theory' ).Tg
            container.Tg_parametrization.SetLineColor(color)
            container.Tg_parametrization.SetMarkerColor(color)
            container.Tg_parametrization.SetLineStyle(1)

            container.Tg_parametrization_expBinning = wsParametrization.GetOutputContainer(
                ct = container.ct , cg = container.cg,
                returnWhat='exp' ).Tg
            container.Tg_parametrization_expBinning.SetLineColor(color)
            container.Tg_parametrization_expBinning.SetMarkerColor(color)
            container.Tg_parametrization_expBinning.SetLineStyle(1)

            containers.append( container )


        # ======================================
        # Additional lines to check

        extraTestCouplings = [
            # { 'ct' : -0.565910458565, 'cg' : 9.62666416168 },
            ]

        extraTestContainers = []
        for testCouplings in extraTestCouplings:
            color = next(colorCycle)

            container = Container(
                name = '_'.join([ '{0}_{1:.2f}'.format(key, value) for key, value in sorted(testCouplings.iteritems()) ])
                )
            container.binBoundaries = containers[0].binBoundaries

            container.Tg_parametrization = wsParametrization.GetOutputContainer(
                ct = testCouplings['ct'] , cg = testCouplings['cg'],
                returnWhat='theory' ).Tg
            container.Tg_parametrization.SetLineColor(color)
            container.Tg_parametrization.SetMarkerColor(color)
            container.Tg_parametrization.SetLineStyle(1)

            container.Tg_parametrization_expBinning = wsParametrization.GetOutputContainer(
                ct = testCouplings['ct'] , cg = testCouplings['cg'],
                returnWhat='exp' ).Tg
            container.Tg_parametrization_expBinning.SetLineColor(color)
            container.Tg_parametrization_expBinning.SetMarkerColor(color)
            container.Tg_parametrization_expBinning.SetLineStyle(1)

            extraTestContainers.append( container )



        # ======================================
        # Make plot

        c.cd()
        c.Clear()
        SetCMargins( RightMargin=0.3 )

        xMinAbs = min([ container.Tg_theory.xMin for container in containers ])
        xMaxAbs = max([ container.Tg_theory.xMax for container in containers ])
        yMinAbs = min([ container.Tg_theory.yMin for container in containers ])
        yMaxAbs = max([ container.Tg_theory.yMax for container in containers ])

        xMin = xMinAbs - 0.1*( xMaxAbs - xMinAbs )
        xMax = xMaxAbs + 0.1*( xMaxAbs - xMinAbs )
        yMin = yMinAbs - 0.1*( yMaxAbs - yMinAbs )
        yMax = yMaxAbs + 0.1*( yMaxAbs - yMinAbs )

        base = GetPlotBase(
            xMin = xMin,
            xMax = xMax,
            yMin = yMin,
            yMax = yMax,
            xTitle = 'p_{T} [GeV]', yTitle = '#mu'
            )
        base.Draw('P')

        leg = ROOT.TLegend(
            1 - 0.3,
            c.GetBottomMargin(),
            1 - 0.02 ,
            1 - c.GetTopMargin() 
            )
        leg.SetBorderSize(0)
        leg.SetFillStyle(0)


        if plotCombination:
            # Combination scan result
            combinationPOIs = Commands.ListPOIs( 'workspaces_May15/combinedCard_May15.root' )
            combinationscans = PhysicsCommands.GetScanResults(
                combinationPOIs,
                'Scan_May15',
                pattern = 'combinedCard'
                )
            TgCombination = PhysicsCommands.GetTGraphForSpectrum( combinationPOIs, combinationscans, name='Combination' )
            TgCombination.SetLineColor(1)
            TgCombination.SetFillColorAlpha( 1, 0.2 )

            CorrelationMatrices.ConvertTGraphToLinesAndBoxes(
                TgCombination,
                drawImmediately=True, legendObject=leg, noBoxes=False, xMaxExternal=xMax )


        for container in containers:
            container.Tg_theory.Draw('XP')
            container.Tg_parametrization.Draw('XL')

            if DrawExperimentalBinLines:
                CorrelationMatrices.ConvertTGraphToLinesAndBoxes(
                    container.Tg_parametrization_expBinning,
                    drawImmediately=True, legendObject=leg, noBoxes=True, xMaxExternal=xMax )

            leg.AddEntry( container.Tg_theory.GetName(), container.name, 'p' )


        for container in extraTestContainers:
            container.Tg_parametrization.Draw('XL')
            if DrawExperimentalBinLines:
                CorrelationMatrices.ConvertTGraphToLinesAndBoxes(
                    container.Tg_parametrization_expBinning,
                    drawImmediately=True, legendObject=leg, noBoxes=True, xMaxExternal=xMax )


        leg.Draw()

        outname = '{0}_parametrizationCheck'.format( basename(wsToCheck) )
        SaveC( outname )




########################################
# End of Main
########################################
if __name__ == "__main__":
    print 'Don\'t run this program directly'