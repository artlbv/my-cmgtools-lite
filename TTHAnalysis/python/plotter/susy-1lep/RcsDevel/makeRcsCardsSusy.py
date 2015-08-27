#!/usr/bin/env python
from CMGTools.TTHAnalysis.plotter.mcAnalysis import *
import re, sys, os, os.path
systs = {}

from searchBins import *

# trees
#Tdir = "/nfs/dust/cms/group/susy-desy/Run2/ACDV/CMGtuples/MC/SPRING15/Spring15/Links/"
#FTdir = "/nfs/dust/cms/group/susy-desy/Run2/ACDV/CMGtuples/MC/SPRING15/Spring15/Links/Friends/"
Tdir = "/nfs/dust/cms/group/susy-desy/Run2/MC/CMGtuples/Spring15/"
FTdir = "/nfs/dust/cms/group/susy-desy/Run2/MC/CMGtuples/Spring15/Friends/"

def addOptions(options):

    # set tree options
    options.path = Tdir
    options.friendTrees = [("sf/t",FTdir+"/evVarFriend_{cname}.root")]
    options.tree = "treeProducerSusySingleLepton"

    # extra options
    options.doS2V = True
    options.weight = True
    options.final  = True
    options.allProcesses  = True
    options.maxEntries = 10


def analyzeReport(options):

    # make MCA and cut vars
    mca  = MCAnalysis(options.mcaFile,options)
    cuts = CutsFile(options.cutFile,options)

    # make bin name and outdir names

    #binname = os.path.basename(options.cutFile).replace(".txt","") if options.outname!=None else options.outname
    binname = options.bin
    if options.outdir == None:
        outdir = "test/"
    else:
        outdir = options.outdir
    #outdir  = options.outdir+"/" if options.outdir!=None else ""
    #outdir = "test/"

    # get report
    if options.pretend:
        report = []
    else:
        report = mca.getPlotsRaw("x", options.var, options.bins, cuts.allCuts(), nodata=options.asimov)

    # add sum MC entry
    if not options.pretend:
        totalMC = []
        for p in mca.listBackgrounds():
            if p in report: totalMC.append(report[p])
            report['x_background'] = mergePlots("x_background", totalMC)

    '''
    if options.asimov:
        tomerge = []
        for p in mca.listBackgrounds():
            if p in report: tomerge.append(report[p])
        report['data_obs'] = mergePlots(binname+"_data_obs", tomerge)
    #else:
    #    report['data_obs'] = report['data'].Clone(binname+"_data_obs")
    '''

    myout = outdir+"/common/"
    if not os.path.exists(myout): os.system("mkdir -p "+myout)

    foutname = myout+binname+".yields.root"
    workspace = ROOT.TFile.Open(foutname, "RECREATE")
    if options.verbose > 0:
        print 'Writing', foutname
        print 'Yields:'

    if not options.pretend:
        for n,h in report.iteritems():
            if options.verbose > 0:
                print "\t%s (%8.3f events)" % (h.GetName(),h.Integral())
            workspace.WriteTObject(h,h.GetName())
    workspace.Close()


def makeCards(options, args):

    addOptions(options)

    if options.verbose > 1:
        print options

    if options.pretend:
        #return 1
        pass

    analyzeReport(options)

    return 1


if __name__ == "__main__":

    from optparse import OptionParser
    parser = OptionParser()

    parser.usage = '%prog [options]'
    parser.description="""
    Make cards for Rcs
    """

    addMCAnalysisOptions(parser)

    # extra options for tty
    parser.add_option("-m","--mca", dest="mcaFile",default="mca-Cards_test.txt",help="MCA sample list")
    parser.add_option("-c","--cuts", dest="cutFile",default="trig_base.txt",help="Baseline cuts file")
    parser.add_option("--binname", dest="binname",default="test",help="Binname")

    # options for cards
    parser.add_option("--var", dest="var",default="1",help="Variable")
    parser.add_option("--bins", dest="bins",default="[0.5,1.5]",help="Histo Bins")

    # I/O options
    parser.add_option("-o",   "--out",    dest="outname", type="string", default=None, help="output name")
    parser.add_option("--od", "--outdir", dest="outdir", type="string", default=None, help="output name")
    ##parser.add_option("-o","--outdir", dest="outdir",default="test", help="out dir for cards")

    # running options
    #parser.add_option("-v","--verbose", dest="verbose",default=False, action="store_true",help="verbose output")
    parser.add_option("-v","--verbose",  dest="verbose",  default=0,  type="int",    help="Verbosity level (0 = quiet, 1 = verbose, 2+ = more)")
    parser.add_option("--pretend", dest="pretend",default=False, action="store_true",help="pretend to do it")

    # batch options
    parser.add_option("-b","--batch", dest="batch",default=False, action="store_true", help="batch command for submission")
    parser.add_option("--jobList","--jobList", dest="jobListName",default="jobList.txt",help="job list name")
    #parser.add_option("-f","--force", dest="force",default=False, action="store_true",help="force mode")

    #makeShapeCards options
    parser.add_option("--asimov", dest="asimov", action="store_true", default=False, help="Make Asimov pseudo-data")
    #parser.add_option("--dummy",  dest="dummyYieldsForZeroBkg", action="store_true", default=False, help="Set dummy yields such it corresponds to 0.01 for 4/fb");
    #parser.add_option("--ignoreEmptySignal",  dest="ignoreEmptySignal", action="store_true", default=False, help="Do not write out a datacard if the expected signal is less than 0.01");

    # Read options and args
    (options,args) = parser.parse_args()

    if options.verbose > 0:
        print 'Arguments', args

    for lt_bin,lt_cut in binsLT.iteritems():

        htbins = []

        if lt_bin in ['LT1']:
            htbins += ['HT0','HT1p2']
        if lt_bin in ['LT1','LT2']:
            htbins += ['HT0']
        if lt_bin in ['LT2']:
            htbins += ['HT1']
        if lt_bin in ['LT2','LT3','LT4']:
            htbins += ['HT2']
        if lt_bin in ['LT3','LT4']:
            htbins += ['HT0p1']

        #for ht_bin,ht_cut in binsHT.iteritems():
        for ht_bin in htbins:
            ht_cut = binsHT[ht_bin]

            nbbins = []

            # Match NB bins
            if lt_bin in ['LT1','LT2','LT3','LT4']:
                nbbins += ['NB1'] # NB1 present in all LT bins
            if lt_bin in ['LT1','LT2','LT3']:
                nbbins += ['NB2','NB3'] # NB1 present in all LT bins
            if lt_bin in ['LT4']:
                nbbins += ['NB2p3'] # NB1 present in all LT bins

            for nb_bin in nbbins:
                nb_cut = binsNB[nb_bin]
            #for nb_bin,nb_cut in binsNB.iteritems():

                binname = "%s_%s_%s" %(lt_bin,ht_bin,nb_bin)
                options.cutsToAdd = [("triggLT",lt_bin,lt_cut),("triggLT",ht_bin,ht_cut),("triggLT",nb_bin,nb_cut)]

                if options.verbose > 0:
                    print 80*'#'
                    print 'Processing bin %s with cuts %s' %(binname,options.cutsToAdd)

                options.bin = binname
                #print options
                makeCards(options, args)
