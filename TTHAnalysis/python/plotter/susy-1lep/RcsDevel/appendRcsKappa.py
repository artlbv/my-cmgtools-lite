#!/usr/bin/env python
#import re, sys, os, os.path

import glob, os, sys
from math import hypot, sqrt
from ROOT import *

from readYields import getYield

def getPnames(fname,tdir):

    tfile = TFile(fname,"READ")
    tfile.cd(tdir)

    pnames = []

    for key in gDirectory.GetListOfKeys():

        obj = key.ReadObj()
        pnames.append(obj.GetName())

    tfile.Close()

    return pnames

def getRcsHist(tfile, hname, band = "SB", merge = True):

    hSR = tfile.Get("SR_"+band+"/"+hname)
    hCR = tfile.Get("CR_"+band+"/"+hname)

    hRcs = hSR.Clone(hSR.GetName().replace('x_','Rcs_'))
    hRcs.Divide(hCR)

    hRcs.GetYaxis().SetTitle("Rcs")

    # merge means ele/mu values are overwritten by the combined Rcs
    if 'data' in hname: merge = True

    if merge:
        rcs = hRcs.GetBinContent(2,2); err = hRcs.GetBinError(2,2) # lep sele

        hRcs.SetBinContent(1,2,rcs); hRcs.SetBinError(1,2,err) # mu sele
        hRcs.SetBinContent(3,2,rcs); hRcs.SetBinError(3,2,err) # ele sele

    return hRcs

def getPredHist(tfile, hname):

    hRcsMB = tfile.Get("Rcs_SB/"+hname)

    if ('data' in hname) or ("background" in hname) or ("poisson" in hname):
        # use EWK template
        hKappa = tfile.Get("Kappa/EWK")
    else:
        hKappa = tfile.Get("Kappa/"+hname)

    # get yield from CR of MB
    hCR_MB = tfile.Get("CR_MB/"+hname)

    hPred = hCR_MB.Clone(hCR_MB.GetName())#+"_pred")
    #hPred.SetTitle("Predicted yield")

    hPred.Multiply(hRcsMB)
    hPred.Multiply(hKappa)

    return hPred

def readQCDratios(fname = "lp_LTbins_NJ34_f-ratios_MC.txt"):

    fDict = {}

    with open(fname) as ftxt:
        lines = ftxt.readlines()

        for line in lines:
            if line[0] != '#':
                (bin,rat,err) = line.split()
                bin = bin.replace("_NJ34","")
                if 'LT' in bin:
                    fDict[bin] = (float(rat),float(err))

    #print 'Loaded f-ratios from file', fname
    #print fDict

    return fDict

def getPoissonHist(tfile, pname = "background", band = "CR_MB"):
    # sets all bin errors to sqrt(N)

    hist = tfile.Get(band+"/"+pname).Clone(pname+"_poisson")

    if "TH" not in hist.ClassName(): return 0

    for ix in range(1,hist.GetNbinsX()+1):
        for iy in range(1,hist.GetNbinsY()+1):
            hist.SetBinError(ix,iy,sqrt(hist.GetBinContent(ix,iy)))

    return hist

def getQCDsubtrHistos(tfile, pname = "background", band = "CR_MB/", isMC = True, lep = "ele"):
    ## returns two histograms:
    ## 1. QCD prediction from anti-leptons
    ## 2. Original histo - QCD from prediction

    fRatio = 0.3 # default
    fRatioErr = 0.01 # default

    fRatios = {}

    if isMC: fRatios = readQCDratios("lp_LTbins_NJ34_f-ratios_MC.txt")
    else: fRatios = readQCDratios("lp_LTbins_NJ34_f-ratios_Data.txt")

    # get bin from filename
    for key in fRatios:
        if key in tfile.GetName():
            (fRatio,fRatioErr) = fRatios[key]
            #print "Found matching ratios for key" , key
            break
        #else: print "No corresp fRatio found! Using default."

    if lep == "ele" :

        hOrig = tfile.Get(band+pname) # original histogram
        if not hOrig: return 0

        ############################
        ## 1. QCD prediction
        hQCDpred = hOrig.Clone(pname+"_QCDpred")
        hQCDpred.Reset() # reset counts/errors

        # take anti-selected ele yields
        yAnti = hOrig.GetBinContent(3,1); yAntiErr = hOrig.GetBinError(3,1);

        # apply f-ratio
        yQCDFromAnti = fRatio*yAnti
        yQCDFromAntiErr = sqrt((yAntiErr*fRatio)**2 + (yAnti*fRatioErr)**2)

        # set bin content for ele
        hQCDpred.SetBinContent(3,2,yQCDFromAnti)
        hQCDpred.SetBinError(3,2,yQCDFromAntiErr)

        # set bin content for lep (=ele)
        hQCDpred.SetBinContent(2,2,yQCDFromAnti)
        hQCDpred.SetBinError(2,2,yQCDFromAntiErr)

        ############################
        ## 2. histo with QCD subtracted
        hQCDsubtr = hOrig.Clone(pname+"_QCDsubtr")

        # do QCD subtraction only in Control Region
        if 'CR' in band:
            # subtract prediction from histo
            hQCDsubtr.Add(hQCDpred,-1)

        return (hQCDpred,hQCDsubtr)
    else:
        print "QCD estimate not yet implemented for muons"
        return 0

def makeQCDsubtraction(fileList):

    # define hists to make QCD estimation
    #pnames = ["background","data","QCD"] # process name
    pnames = ["background","QCD"] # process name
    pnames += ["background_poisson","QCD_poisson"] # process name

    bindirs =  ['SR_MB','CR_MB','SR_SB','CR_SB']

    for fname in fileList:
        tfile = TFile(fname,"UPDATE")

        for pname in pnames:
            for bindir in bindirs:

                if 'data' in pname: isMC = False
                else: isMC = True

                #hNew = getQCDsubtrHisto(tfile,pname,bindir+"/",isMC)
                ret  = getQCDsubtrHistos(tfile,pname,bindir+"/",isMC)

                if not ret:
                    print 'Could not create new histo for', pname, 'in bin', bindir
                else:
                    (hQCDpred,hQCDsubtr) = ret
                    tfile.cd(bindir)
                    #hNew.Write()
                    hQCDpred.Write()
                    hQCDsubtr.Write()
                tfile.cd()

        tfile.Close()

def makePoissonErrors(fileList):

    # define hists to make make poisson errors
    pnames = ["background","QCD","EWK"] # process name

    bindirs =  ['SR_MB','CR_MB','SR_SB','CR_SB']

    for fname in fileList:
        tfile = TFile(fname,"UPDATE")

        for pname in pnames:
            for bindir in bindirs:

                hist = getPoissonHist(tfile,pname,bindir)

                if hist:
                    tfile.cd(bindir)
                    # overwrite old hist
                    hist.Write()#"",TObject.kOverwrite)
                tfile.cd()

        tfile.Close()

def makeKappaHists(fileList):

    # filter
    #fileList = [fname for fname in fileList if 'NB3' not in fname]

    pnames = ["x_background","x_EWK"] # process name
    pnames = getPnames(fileList[0],'SR_MB') # get process names from file

    print 'Found these hists:', pnames

    bindirs =  ['SR_MB','CR_MB','SR_SB','CR_SB']
    #print bindirs

    for fname in fileList:
        tfile = TFile(fname,"UPDATE")

        #getQCDpred(tfile, 'MB')

        # create Rcs/Kappa dir struct
        if not tfile.GetDirectory("Rcs_MB"):
            tfile.mkdir("Rcs_MB")
            tfile.mkdir("Rcs_SB")
            tfile.mkdir("Kappa")

            for pname in pnames:

                hRcsMB = getRcsHist(tfile, pname, 'MB')
                hRcsSB = getRcsHist(tfile, pname, 'SB')

                # make kappa
                hKappa = hRcsMB.Clone(hRcsMB.GetName().replace('Rcs','Kappa'))
                hKappa.Divide(hRcsSB)

                hKappa.GetYaxis().SetTitle("Kappa")

                tfile.cd("Rcs_MB")
                hRcsMB.Write()

                tfile.cd("Rcs_SB")
                hRcsSB.Write()

                tfile.cd("Kappa")
                hKappa.Write()

        else:
            pass
            #print 'Already found Rcs and Kappa'

            '''
            yList = []
            print 'Yields for', pname
            for bindir in bindirs:
                yList.append(getYield(tfile,pname,bindir))

            print yList
            '''

        tfile.Close()

    return 1

def makePredictHists(fileList):

    # get process names from file
    pnames = getPnames(fileList[0],'SR_MB')

    print 'Found these hists:', pnames

    #bindirs =  ['SR_MB','CR_MB','SR_SB','CR_SB']

    for fname in fileList:
        tfile = TFile(fname,"UPDATE")

        # create Rcs/Kappa dir struct
        if not tfile.GetDirectory("SR_MB_predict"):
            tfile.mkdir("SR_MB_predict")

            for pname in pnames:

                hPredict = getPredHist(tfile,pname)

                if hPredict:
                    tfile.cd("SR_MB_predict")
                    hPredict.Write()
                    #print "Wrote prediction of", pname
                else:
                    print "Failed to make prediction for", pname
        else:
            pass

        tfile.Close()

    return 1

def makeClosureHists(fileList):

    pnames = getPnames(fileList[0],'SR_MB') # get process names from file
    #print 'Found these hists:', pnames

    bindirs =  ['SR_MB','CR_MB','SR_SB','CR_SB']

    for fname in fileList:
        tfile = TFile(fname,"UPDATE")

        # create Closure dir
        if not tfile.GetDirectory("Closure"):
            tfile.mkdir("Closure")

        for pname in pnames:

            hPred = tfile.Get("SR_MB_predict/"+pname)#+"_pred")
            hObs = tfile.Get("SR_MB/"+pname)

            hDiff = hObs.Clone(hObs.GetName())#+"_diff")
            hDiff.Add(hPred,-1)

            #hDiff.GetYaxis().SetTitle("Observed - Predicted/Observed")
            hDiff.Divide(hObs)

            tfile.cd("Closure")
            hDiff.Write()

        tfile.Close()

    return 1

if __name__ == "__main__":

    ## remove '-b' option
    _batchMode = False

    if '-b' in sys.argv:
        sys.argv.remove('-b')
        _batchMode = True

    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        print '# pattern is', pattern
    else:
        print "No pattern given!"
        exit(0)


    # append / if pattern is a dir
    if os.path.isdir(pattern): pattern += "/"

    # find files matching pattern
    fileList = glob.glob(pattern+"*.root")

    makePoissonErrors(fileList)
    makeQCDsubtraction(fileList)
    makeKappaHists(fileList)
    makePredictHists(fileList)
    makeClosureHists(fileList)

    print 'Finished'
