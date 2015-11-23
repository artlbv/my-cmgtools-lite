import sys,os

from makeYieldPlots import *

_batchMode = False

if __name__ == "__main__":

    ## remove '-b' option
    if '-b' in sys.argv:
        sys.argv.remove('-b')
        _batchMode = True

    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        print '# pattern is', pattern
    else:
        print "No pattern given!"
        exit(0)

    #BinMask LTX_HTX_NBX_NJX for canvas names
    basename = os.path.basename(pattern)
    mask = basename.replace("*","X_")

    ## Create Yield Storage
    yds = YieldStore("lepYields")
    yds.addFromFiles(pattern,("lep","sele"))
    yds.showStats()

    # update colors
    colorDict["QCD_pred"] = kBlue
    colorDict["QCD_exp"] = kRed

    lumi = 3

    CMS_lumi.lumi_13TeV = str(lumi) + " fb^{-1}"
    CMS_lumi.extraText = "Simulation"

    # Category
    #cat = "CR_MB"
    cats = ["CR_MB","CR_SB"]

    for cat in cats:

        hQCDexp = makeSampHisto(yds,"QCD",cat,"QCD_exp"); hQCDexp.SetTitle("QCD (MC)")
        hQCDpred = makeSampHisto(yds,"QCD_QCDpred",cat,"QCD_pred"); hQCDpred.SetTitle("QCD (Predicted)")

        ratio = getPull(hQCDexp,hQCDpred)
        #ratio.GetYaxis().SetRangeUser(0,5)

        canv = plotHists("QCDcheck_"+cat,[hQCDexp,hQCDpred],ratio)

        if not _batchMode:
            if "q" in raw_input("Enter any key to exit (or 'q' to stop): "): exit(0)

        exts = [".pdf",".png"]
        for ext in exts:
            canv.SaveAs("BinPlots/QCD/"+mask+canv.GetName()+ext)
