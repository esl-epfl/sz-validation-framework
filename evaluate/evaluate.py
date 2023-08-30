import sys
import os
sys.path.insert(1, os.path.join(sys.path[0],'..'))
import pandas as pd
import re
from timescoring import scoring
from timescoring.annotations import Annotation
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import datetime


def dfToEvents(df: pd.DataFrame) -> list[tuple[float, float]]:
    ''' Converts form starts and stops in annotation file to events for performance metrics evaluation.
    Args:
        df: Dataframe annotation file
    Returns: List of events with start and stop times.
    '''
    events = list()
    for _, row in df.sort_values(by=['startTime']).iterrows():
        if re.search(r'sz.*', row.event):
            events.append((row.startTime, row.endTime))
    return events

def evaluate2AnnotationFiles(refFilename: str, hypFilename: str, labelFreq,  params) -> pd.DataFrame:
    ''' Compares two annotation files in the same format. One are reference true annotations and other
    one are predicted hypothesis by the ML algorithm. Goes one by one file in the annotations file and performs matching of
    the true and predicted labels and calculated various performances for individual file in annotations files.

    Args:
        refFilename: Filename of the file containing true annotations.
        hypFilename: Filename of the file containing predicted annotations.
        labelFreq: Sampling resolution of labels.
        params: Class with various parameters for scoring on the event basis.
    Returns: Dataframe containing various performances per each file.
    '''
    results = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'Event_numEvents': [],
        'Event_numTP':[],
        'Event_numFP':[],
        'Event_numFN':[],
        'Event_sensitivity': [],
        'Event_precision': [],
        'Event_f1': [],
        'Event_fpRate': [],
        'Sample_numEvents': [],
        'Sample_numTP': [],
        'Sample_numFP': [],
        'Sample_numFN': [],
        'Sample_sensitivity': [],
        'Sample_precision': [],
        'Sample_f1': [],
        'SampleEvent_f1mean': [],
        'SampleEvent_f1gmean': [],
        'filepath': [],
    }

    refDf = pd.read_csv(refFilename)
    hypDf = pd.read_csv(hypFilename)

    for filepath, _ in refDf.groupby(['filepath']):
        # fs = 256
        nSamples = round(refDf[refDf.filepath == filepath].duration.iloc[0] * labelFreq)

        # Convert annotations
        ref = Annotation(dfToEvents(refDf[refDf.filepath == filepath]), labelFreq, nSamples)
        hyp = Annotation(dfToEvents(hypDf[hypDf.filepath == filepath]), labelFreq, nSamples)

        # Compute performance
        scoresEvent = scoring.EventScoring(ref, hyp, params)
        scoresSample = scoring.SampleScoring(ref, hyp)

        # Collect results
        for key in ['subject', 'session', 'recording', 'dateTime', 'duration', 'filepath']:
            results[key].append(refDf[refDf.filepath == filepath][key].iloc[0])
        results['Event_numEvents'].append(scoresEvent.refTrue)
        results['Event_numTP'].append(scoresEvent.tp)
        results['Event_numFP'].append(scoresEvent.fp)
        results['Event_numFN'].append(scoresEvent.refTrue- scoresEvent.tp)
        results['Event_sensitivity'].append(scoresEvent.sensitivity)
        results['Event_precision'].append(scoresEvent.precision)
        results['Event_f1'].append(scoresEvent.f1)
        results['Event_fpRate'].append(scoresEvent.fpRate)
        results['Sample_numEvents'].append(scoresSample.refTrue)
        results['Sample_numTP'].append(scoresSample.tp)
        results['Sample_numFP'].append(scoresSample.fp)
        results['Sample_numFN'].append(scoresSample.refTrue - scoresSample.tp)
        results['Sample_sensitivity'].append(scoresSample.sensitivity)
        results['Sample_precision'].append(scoresSample.precision)
        results['Sample_f1'].append(scoresSample.f1)
        results['SampleEvent_f1mean'].append((scoresSample.f1+scoresEvent.f1)/2)
        results['SampleEvent_f1gmean'].append(np.sqrt(scoresSample.f1 * scoresEvent.f1) )

    return pd.DataFrame(results)

# def  recalculatePerfPerSubject(performancePerFile, subjects, labelFreq):
def recalculatePerfPerSubject(performancePerFile, subjects, labelFreq, params):
    ''' Uses output from evaluate2AnnotationFiles which contains performance per each file of the dataset,
    and calculated performance per subject.

    Args:
        performancePerFile: Dataframe with performance per each file. It is output of evaluate2AnnotationFiles function.
        subjects: Subjects for which to calculate performance.
        labelFreq: Sampling resolution of labels.
        params: Class with various parameters for scoring on the event basis.

    Returns: Dataframe containing various performances per each subject.
    '''

    results = {
        'subject': [],
        'duration': [],
        'Event_numEvents': [],
        'Event_numTP':[],
        'Event_numFP':[],
        'Event_numFN':[],
        'Event_sensitivity': [],
        'Event_precision': [],
        'Event_f1': [],
        'Event_fpRate': [],
        'Sample_numEvents': [],
        'Sample_numTP': [],
        'Sample_numFP': [],
        'Sample_numFN': [],
        'Sample_sensitivity': [],
        'Sample_precision': [],
        'Sample_f1': [],
        'SampleEvent_f1mean': [],
        'SampleEvent_f1gmean': [],
    }

    for patIndx, pat in enumerate(subjects):
        dataThisSubj = performancePerFile.loc[performancePerFile['filepath'].str.contains(pat, case=False)].reset_index( drop=True)
        nSamples = int(np.sum(dataThisSubj.duration.to_numpy()))
        events = [(1, 3), (6, 9)]  # just sth random
        ref = Annotation(events, labelFreq, nSamples)
        scoresEvent = scoring.EventScoring(ref, ref, params)
        scoresEvent.refTrue = np.sum(dataThisSubj.Event_numEvents.to_numpy())
        scoresEvent.tp = np.sum(dataThisSubj.Event_numTP.to_numpy())
        scoresEvent.fp = np.sum(dataThisSubj.Event_numFP.to_numpy())
        scoresEvent.computeScores()
        scoresSample = scoring.SampleScoring(ref, ref)
        scoresSample.refTrue = np.sum(dataThisSubj.Sample_numEvents.to_numpy())
        scoresSample.tp = np.sum(dataThisSubj.Sample_numTP.to_numpy())
        scoresSample.fp = np.sum(dataThisSubj.Sample_numFP.to_numpy())
        scoresSample.computeScores()

        results['subject'].append(pat)
        results['duration'].append(nSamples)
        results['Event_numEvents'].append(scoresEvent.refTrue)
        results['Event_numTP'].append(scoresEvent.tp)
        results['Event_numFP'].append(scoresEvent.fp)
        results['Event_numFN'].append(scoresEvent.refTrue- scoresEvent.tp)
        results['Event_sensitivity'].append(scoresEvent.sensitivity)
        results['Event_precision'].append(scoresEvent.precision)
        results['Event_f1'].append(scoresEvent.f1)
        results['Event_fpRate'].append(scoresEvent.fpRate)
        results['Sample_numEvents'].append(scoresSample.refTrue)
        results['Sample_numTP'].append(scoresSample.tp)
        results['Sample_numFP'].append(scoresSample.fp)
        results['Sample_numFN'].append(scoresSample.refTrue - scoresSample.tp)
        results['Sample_sensitivity'].append(scoresSample.sensitivity)
        results['Sample_precision'].append(scoresSample.precision)
        results['Sample_f1'].append(scoresSample.f1)
        results['SampleEvent_f1mean'].append((scoresSample.f1+scoresEvent.f1)/2)
        results['SampleEvent_f1gmean'].append(np.sqrt(scoresSample.f1 * scoresEvent.f1) )

    return pd.DataFrame(results)


def plotPerformancePerSubj(patients, performanceResults, folderOut):
    ''' Simple performance per subject.

    Args:
        patients: Subjects to plot performance for.
        performanceResults: Dataframe with performance results. It is output from recalculatePerfPerSubject function.
        folderOut: Folder in which to save figure.
    '''
    perfNames = ['Event_sensitivity', 'Event_precision', 'Event_f1', 'Sample_sensitivity',
                 'Sample_precision', 'Sample_f1', 'SampleEvent_f1mean', 'SampleEvent_f1gmean', 'Event_fpRate']
    perfNamesShrt = ['E sens', 'E prec', 'E f1', 'S sens', 'S prec', 'S f1', 'ES f1mean', 'ES f1gmean', 'fpRate']

    # plot performance measures per subject
    fig1 = plt.figure(figsize=(10, 10), constrained_layout=False)
    gs = GridSpec(3, 3, figure=fig1)
    fig1.subplots_adjust(wspace=0.35, hspace=0.35)
    # fig1.suptitle('All subject different performance measures ')
    xValues = np.arange(1, len(patients) + 1, 1)
    numPerf = len(perfNames)
    for perfIndx, perf in enumerate(perfNames):
        ax1 = fig1.add_subplot(gs[int(np.floor(perfIndx / 3)), np.mod(perfIndx, 3)])
        ax1.plot(xValues, performanceResults.loc[:, perf].to_numpy(), 'k')
        #plot mean
        ax1.plot(xValues, np.ones(len(xValues)) * np.nanmean(performanceResults.loc[:, perf].to_numpy()), 'b')
        ax1.set_xlabel('Subjects')
        ax1.set_title(perf)
        ax1.grid()
    fig1.show()
    fig1.savefig(folderOut + '/AllSubj_AllPerformanceMeasures.png', bbox_inches='tight')
    plt.close(fig1)

    # plot performance for all subj in form of boxplot
    fig1 = plt.figure(figsize=(12, 6), constrained_layout=False)
    gs = GridSpec(1, 1, figure=fig1)
    ax1 = fig1.add_subplot(gs[0,0])
    fig1.subplots_adjust(wspace=0.3, hspace=0.3)
    xValues = np.arange(0, len(perfNamesShrt)-1, 1)
    dataToPlot = performanceResults.loc[:, perfNames[0:-1]].to_numpy()
    mask = ~np.isnan(dataToPlot)
    filtData = [d[m] for d, m in zip(dataToPlot.T, mask.T)]
    ax1.boxplot(filtData, positions=[0,1, 2, 3, 4, 5, 6, 7])
    ax1.set_xticks(xValues)
    ax1.set_xticklabels(perfNamesShrt[0:-1], fontsize=10)  # , rotation=45)
    ax1.set_ylabel('Performance')
    ax1.grid()
    fig1.show()
    ax1.set_title('Performance distribution for all subjects')
    fig1.savefig(folderOut + '/AllSubj_AllPerformanceMeasures_Boxplot.png', bbox_inches='tight')
    fig1.savefig(folderOut + '/AllSubj_AllPerformanceMeasures_Boxplot.svg', bbox_inches='tight')
    plt.close(fig1)


def createAnnotationFileFromPredictions(data, annotationTrue, labelColumnName):
    ''' Creates annotation file from predictions in time.
    Args:
        data:
        annotationTrue: True annotation dataframe. Borrows from it some of the information.
        labelColumnName: Name of the column with labels.
    Returns: Dataframe of the same format as true annotations dataframe.
    '''

    annotations = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'event': [],
        'startTime': [],
        'endTime': [],
        'confidence': [],
        'channels': [],
        'filepath': []
    }
    annotationAllPred = pd.DataFrame(annotations)
    columnsToKeep=['subject','session','recording','dateTime', 'duration']

    fileNamesTL=set(annotationTrue["filepath"].to_numpy())
    fileNamesTL = list(fileNamesTL)
    fileNamesTL.sort()
    fileNamesPL=set(data["FileName"].to_numpy())
    fileNamesPL = list(fileNamesPL)
    fileNamesPL.sort()
    for fn in fileNamesPL:
        dataThisFile=data.loc[data['FileName'] == fn].reset_index(drop=True)
        d = dataThisFile[labelColumnName].to_numpy()
        startIndx=np.where(np.diff(d) == 1)[0]+1
        endIndx = np.where(np.diff(d) == -1)[0]+1
        # if (len(d)>0):
        if (d[len(d)-1]==1):
            endIndx=np.append(endIndx, len(d)-1)
        elif  (d[0]==1 and startIndx[0]!=0):
            startIndx= np.insert(startIndx, 0,0)
        indxAnnotTrue=annotationTrue.index[annotationTrue['filepath']==fn].tolist()
        fixInfo=annotationTrue.loc[indxAnnotTrue, columnsToKeep]
        if (len(startIndx)==0): #no seizures detected, only add bckg
            row = np.asarray(['bckg', 0, fixInfo.loc[indxAnnotTrue[0], 'duration'], 1.0, 'all', fn])
            rowDF = pd.DataFrame(row.reshape((1, -1)),columns=['event', 'startTime', 'endTime', 'confidence', 'channels', 'filepath'])
            fullRowDF = pd.concat([fixInfo.reset_index(drop=True), rowDF.reset_index(drop=True)], axis=1)
            annotationAllPred = pd.concat([annotationAllPred, fullRowDF], axis=0)
        else:
            for i, s in enumerate(startIndx):
                startTime=dataThisFile.loc[startIndx[i],'Time']-datetime.datetime.strptime(fixInfo.loc[indxAnnotTrue[0],'dateTime'],  "%Y-%m-%d %H:%M:%S")
                endTime = dataThisFile.loc[endIndx[i], 'Time'] - datetime.datetime.strptime(fixInfo.loc[indxAnnotTrue[0], 'dateTime'],   "%Y-%m-%d %H:%M:%S")
                if (startTime.total_seconds()<0 or endTime.total_seconds()<0):
                    print('time negative ')
                avrgConf= np.mean(data.loc[startIndx[i]:endIndx[i], 'ProbabLabels'].to_numpy())
                row=np.asarray(['sz', startTime.total_seconds(), endTime.total_seconds(), avrgConf, 'all', fn ])
                rowDF=pd.DataFrame(row.reshape((1,-1)), columns=['event', 'startTime', 'endTime', 'confidence', 'channels','filepath'])
                fullRowDF=pd.concat([fixInfo.reset_index(drop=True), rowDF.reset_index(drop=True)], axis=1)
                annotationAllPred=pd.concat([annotationAllPred,fullRowDF], axis=0)

    return(annotationAllPred)
