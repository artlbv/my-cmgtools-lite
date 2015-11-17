#!/usr/bin/env python

import os, glob, sys

from ROOT import *
from searchBins import *
from readYields import getLepYield, getScanYields

class BinYield:
    ## Simple class for yield,error storing (instead of tuple)

    def __init__(self, sample, cat, (val, err)):
        self.name = sample
        self.cat = cat
        self.val = val
        self.err = err

    # func that is called with print BinYield object
    def __repr__(self):
        return "%s : %s : %4.2f +- %4.2f" % (self.name, self.cat, self.val, self.err)

class YieldStore:

    ## Class to store all yields from bin files
    ##
    ## Yields are stored in a dict with:
    ## -- key = (binName,category,sample) where category is SR_SB,Rcs,Kappa,etc
    ## -- value = (yield,error)

    def __init__(self,name):
        self.name = name

        self.yields = {} # yields in dictionary of type d[sample][category][bin] = (yield,err)
        self.bins = [] # list of all bins stored
        self.categories = [] # list of all categories available
        self.samples = [] # list of all samples available

    def addYield(self, sample, category, bin, yd):

        # create dict structure if empty and add to list storages
        if sample not in self.yields: self.yields[sample] = {}
        if sample not in self.samples: self.samples.append(sample)

        if category not in self.yields[sample]: self.yields[sample][category] = {}
        if category not in self.categories:     self.categories.append(category)

        if bin not in self.bins: self.bins.append(bin)

        # add bin yield
        self.yields[sample][category][bin] = yd
        #print "Adding", sample, category, bin, "with", yd

        return 1

    def addBinYields(self, fname, leptype = ("lep","sele")):

        # Open file and get bin name
        tfile = TFile(fname,"READ")
        bfname = os.path.basename(fname)
        binName = bfname.replace("_SR.merge.root","")
        binName = binName.replace(".merge.root","")
        #print binName

        # get list of dirs
        dirList = [dirKey.ReadObj() for dirKey in gDirectory.GetListOfKeys() if dirKey.IsFolder() == 1]

        # Loop over yield categories
        for catDir in dirList:
            catDir.cd()
            category = catDir.GetName()

            # get list of histograms
            histList = [histKey.ReadObj() for histKey in gDirectory.GetListOfKeys() if histKey.IsFolder() != 1]

            ## Loop over hists and save to dicts
            for hist in histList:

                sample = hist.GetName()


                if ('Scan' not in sample) and ('scan' not in sample):
                    # get normal sample yield
                    yd = BinYield(sample, category, getLepYield(hist, leptype))
                    self.addYield(sample,category,binName,yd)
                else:
                    # get yields from scan
                    yds = getScanYields(hist,leptype)
                    # loop over mass points
                    for mGo,mLSP in yds:
                        # selected key type: mass point string or tuple
                        point = sample + "_mGo%i_mLSP%i" %(mGo,mLSP)
                        #point = (mGo,mLSP)

                        yd = BinYield(point, category, yds[(mGo,mLSP)])
                        self.addYield(point,category,binName,yd)

        return 1

    def addFromFiles(self, pattern, leptype = ("lep","sele") ):

        # append / if pattern is a dir
        if os.path.isdir(pattern): pattern += "/"

        # find files matching pattern
        fileList = glob.glob(pattern+"*.root")
        nFiles = len(fileList)

        print "## Starting to add yields from %i files like " %(nFiles) + pattern + ": ", ; sys.stdout.flush()
        # progress bar
        progbar_width = nFiles
        # setup progbar
        sys.stdout.write("[%s]" % (" " * progbar_width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (progbar_width+1)) # return to start of line, after '['

        for fname in fileList:
            #print "\b#",
            sys.stdout.write("-")
            sys.stdout.flush()
            self.addBinYields(fname,leptype)

        print "> done."

        return 1

    def showStats(self):
        print 80*"#"
        print "Storage contains:"
        print len(self.bins), "Bins:", self.bins
        print len(self.categories), "Categories:", self.categories
        print len(self.samples), "Samples:", self.samples
        print 80*"#"

    ###########################
    ## Reading functions follow
    ###########################

    def getBinYield(self,samp,cat,bin):

        if samp in self.yields:
            if cat in self.yields[samp]:
                if bin in self.yields[samp][cat]:
                    return self.yields[samp][cat][bin]
        return 0

    def getSampDict(self,samp,cat):

        if samp in self.samples and cat in self.categories:
            return self.yields[samp][cat]
        else: return 0

    def getSampsDict(self,samp,cats = []):

        yds = {}

        for bin in self.bins:
            yds[bin] = []
            for cat in cats:
                yds[bin].append(self.getBinYield(samp,cat,bin))
        return yds

    def getMixDict(self, samps = []):
        # provide dict: sample - category
        # return dict: bin - yields (corresp to sample,cat)

        yds = {}
        for bin in self.bins:
            yds[bin] = []

            for samp,cat in samps:
                yds[bin].append(self.getBinYield(samp,cat,bin))

        return yds

    def printBins(self, samp,cat):
        if type(cat) == str:
            yds = self.getSampDict(samp,cat)
        elif type(cat) == list:
            yds = self.getSampsDict(samp,cat)
        else:
            print "You have to give either a string or a list of strings"
            return 0

        print 80*"-"
        print "Contents for sample %s and category %s" %(samp,cat)
        #print "Bin\tYield+-Error"

        for bin in sorted(yds.keys()):
            print bin,"\t", yds[bin]
        print 80*"-"

        return 1

    def printMixBins(self, samps):

        yds = self.getMixDict(samps)

        print 80*"-"
        print "Contents for", samps
        print "Bin\tYield+-Error"

        for bin in sorted(yds.keys()):
            print bin,"\t\t",
            for yd in yds[bin]: print yd,"\t",
            print

        return 1

    def printLatexTable(self, samps, printSamps, label, f):
        yds = self.getMixDict(samps)
        nSource = len(samps)
        nCol = nSource + 4
        precision = 5
        f.write('\multicolumn{' + str(nCol) + '}{|c|}{' +label +'} \\\ \\hline \n')
        f.write('$L_T$ & $H_T$ & nB & binName &' +  ' %s ' % ' & '.join(map(str, printSamps)) + ' \\\ \n')
        f.write(' $[$ GeV $]$  &   $[$GeV$]$ & &  '  + (nSource *'%(tab)s  ') % dict(tab = '&') + ' \\\ \\hline \n')

        bins = sorted(yds.keys())
        for i,bin in enumerate(bins):
            (LTbin, HTbin, Bbin ) = bin.split("_")[0:3]
            (LT, HT, B) = (binsLT[LTbin][1],binsHT[HTbin][1],binsNB[Bbin][1])
            (LT0, HT0, B0 ) = ("","","")
            if i > 0 :
                (LT0bin, HT0bin, B0bin ) = bins[i-1].split("_")[0:3]
                (LT0, HT0, B0) = (binsLT[LT0bin][1],binsHT[HT0bin][1],binsNB[B0bin][1])
            if LT != LT0:
                f.write(('\\cline{1-%s} ' + LT + ' & ' + HT + ' & ' + B + '&' + LTbin +', ' + HTbin + ', ' + Bbin) % (nCol))
            if LT == LT0 and HT != HT0:
                f.write(('\\cline{2-%s}  & ' + HT + ' & ' + B + '&' + LTbin +', ' + HTbin + ', ' + Bbin) % (nCol))
            elif LT == LT0 and HT == HT0:
                f.write('  &  & ' + B + '&' + LTbin +', ' + HTbin + ', ' + Bbin)

            print yds[bin]
            for yd in yds[bin]:
                if yd == 0:
                    f.write((' & %.'+str(precision)+'f $\pm$ %.'+str(precision)+'f') % (0.0, 0.0))
                else:
                    f.write((' & %.'+str(precision)+'f $\pm$ %.'+str(precision)+'f') % (yd.val, yd.err))


            f.write(' \\\ \n')
        f.write(' \\hline \n')
        return 1



if __name__ == "__main__":

    import sys

    ## remove '-b' option
    if '-b' in sys.argv:
        sys.argv.remove('-b')

    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        print '## pattern is', pattern
    else:
        print "No pattern given!"
        exit(0)

    yds = YieldStore("bla")
    yds.addFromFiles(pattern)

    yds.showStats()

    #yds.printBins("QCD","CR_SB")
    #yds.getSampsDict("QCD",["CR_SB","CR_MB"])
    #yds.printBins("QCD",["CR_SB","CR_MB"])
    #yds.printBins("data",yds.categories)

    '''
    #samps = {"EWK":"CR_MB","QCD":"CR_SB"}
    #samps = {"EWK":"CR_SB","background_QCDsubtr":"CR_SB","background_QCDsubtr":"Closure"}
    samps = [
        ("QCD","CR_SB"),
        ("QCD_QCDpred","CR_SB"),
        ("QCD_QCDsubtr","CR_SB"),
        ]
    #print yds.getMixDict(samps)
    yds.printMixBins(samps)

    #print yds.yields

    '''
    cat = "SR_MB"

    samps = [
        #("EWK",cat),
        ("T1tttt_Scan_mGo1500_mLSP100",cat),
        ("T1tttt_Scan_mGo1200_mLSP800",cat),
        ]
    #print yds.getMixDict(samps)
    yds.printMixBins(samps)

    print [s for s in yds.samples if "1500" in s]
