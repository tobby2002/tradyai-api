#!/bin/python


from . import halt
from . import Settings

from time import sleep
from random import choice, randrange
from subprocess import Popen, PIPE
from threading import Thread
from .evolution_generations import gekko_generations

import datetime
import os


import promoterz
from version import VERSION
import evaluation


def showTitleDisclaimer(backtestsettings):
    TITLE = """\tGEKKO
        ██╗ █████╗ ██████╗  ██████╗ ███╗   ██╗██╗ ██████╗██╗   ██╗███████╗
        ██║██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██║██╔════╝██║   ██║██╔════╝
        ██║███████║██████╔╝██║   ██║██╔██╗ ██║██║██║     ██║   ██║███████╗
   ██   ██║██╔══██║██╔═══╝ ██║   ██║██║╚██╗██║██║██║     ██║   ██║╚════██║
   ╚█████╔╝██║  ██║██║     ╚██████╔╝██║ ╚████║██║╚██████╗╚██████╔╝███████║
    ╚════╝ ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═════╝ ╚══════╝"""
    try:
        print(TITLE)
    except UnicodeEncodeError or SyntaxError:
        print("\nJAPONICUS\n")
    print('\t' * 8 + 'v%.2f' % VERSION)
    print()

    profitDisclaimer = "The profits reported here depends on backtest interpreter function;"
    interpreterFuncName = backtestsettings['interpreteBacktestProfit']
    interpreterInfo = evaluation.gekko.backtest.getInterpreterBacktestInfo(
        interpreterFuncName)

    print("%s \n\t%s" % (profitDisclaimer, interpreterInfo))


def launchGekkoChildProcess(settings):
    gekko_args = [
        'node',
        '--max-old-space-size=8192',
        settings['global']['gekkoPath'] + '/web/server.js',
    ]
    gekko_server = Popen(gekko_args, stdin=PIPE, stdout=PIPE)
    return gekko_server


def launchWebEvolutionaryInfo():
    print("WEBSERVER MODE")
    webpageTitle = "japonicus evolutionary statistics - v%.2f" % VERSION
    webServer = promoterz.webServer.core.run_server(webpageTitle)
    webServerProcess = Thread(
        target=webServer.server.run,
        kwargs={
            'debug': False,
            'host': '0.0.0.0'
        }
    )
    webServerProcess.start()
    return webServer


def buildJaponicusOptions(optionparser):
    settings = Settings.getSettings()

    # PARSE GENCONF & DATASET COMMANDLINE ARGUMENTS;
    settingSubsets = ['generations', 'dataset', 'backtest', 'evalbreak']
    for settingSubset in settingSubsets:
        parser = promoterz.metaPromoterz.generateCommandLineArguments(
            optionparser,
            settings[settingSubset])

    options, args = parser.parse_args()
    for settingSubset in settingSubsets:
        settings[settingSubset] =\
            promoterz.metaPromoterz.applyCommandLineOptionsToSettings(
            options,
            settings[settingSubset]
        )

    return settings, options


def launchJaponicus(settings, options):
    # ABORT WHEN ILLEGAL OPTIONS ARE SET;
    if not options.genetic_algorithm and not options.bayesian_optimization:
        exit("Aborted: No operation specified.")
    if not os.path.isfile(settings['global']['gekkoPath'] + '/gekko.js'):
        exit("Aborted: gekko.js not found on path specified @Settings.py;")

    # show title;
    showTitleDisclaimer(settings['backtest'])

    # ADDITIONAL MODES;
    gekko_server = launchGekkoChildProcess(settings)\
        if options.spawn_gekko else None
    web_server = launchWebEvolutionaryInfo()\
        if options.spawn_web else None
    sleep(1)
    markzero_time = datetime.datetime.now()

    print()

    # LOCATE & VALIDATE RUNNING GEKKO INSTANCES FROM CONFIG URLs;
    possibleInstances = settings['global']['GekkoURLs']
    validatedInstances = []
    for instance in possibleInstances:
        Response = evaluation.gekko.API.checkInstance(instance)
        if Response:
            validatedInstances.append(instance)
            print("found gekko @ %s" % instance)
        else:
            print("unable to locate %s" % instance)

    if validatedInstances:
        settings['global']['GekkoURLs'] = validatedInstances
    else:
        exit("Aborted: No running gekko instances found.")

    # --SELECT STRATEGY;
    if options.random_strategy:
        Strategy = ""
        GekkoStrategyFolder = os.listdir(settings['global']['gekkoPath'] + '/strategies')
        while Strategy + '.js' not in GekkoStrategyFolder:
            if Strategy:
                print(
                    "Strategy %s descripted on settings but not found on strat folder." %
                    Strategy
                )
            Strategy = choice(list(settings['strategies'].keys()))
            print("> %s" % Strategy)
    elif options.strategy:
        Strategy = options.strategy
    elif not options.skeleton:
        exit("No strategy specified! Use --strat or go --help")

    # --LAUNCH GENETIC ALGORITHM;
    if options.genetic_algorithm:
        GenerationMethod = 'chromosome' if options.chromosome_mode else 'oldschool'
        if options.skeleton:
            EvaluationMode = 'indicator'
            AllIndicators = Settings.getSettings()['indicators']
            TargetParameters = Settings.getSettings()['skeletons'][options.skeleton]
            for K in AllIndicators.keys():
                if type(AllIndicators[K]) != dict:
                    TargetParameters[K] = AllIndicators[K]
                elif AllIndicators[K]['active']:
                    TargetParameters[K] = AllIndicators[K]
                    TargetParameters[K]['active'] = (0, 1)
            if not TargetParameters:
                exit("Bad configIndicators!")
        else:
            EvaluationMode = Strategy

            # READ STRATEGY PARAMETER RANGES FROM TOML;
            try:
                TOMLData = promoterz.TOMLutils.preprocessTOMLFile(
                    "strategy_parameters/%s.toml" % Strategy
                )
            except FileNotFoundError:
                print("Failure to find strategy parameter rules for " +
                      "%s at ./strategy_parameters" % Strategy)
                gekkoParameterPath = "%s/config/strategies/%s.toml" %\
                                     (settings['global']['gekkoPath'], Strategy)
                print("Trying to locate gekko parameters at %s" %
                      gekkoParameterPath)
                TOMLData = promoterz.TOMLutils.preprocessTOMLFile(gekkoParameterPath)

            TargetParameters = promoterz.TOMLutils.TOMLToParameters(TOMLData)
        # RUN ONE EQUAL INSTANCE PER REPEATER NUMBER SETTINGS, SEQUENTIALLY;
        for s in range(options.repeater):
            gekko_generations(
                TargetParameters, GenerationMethod,
                EvaluationMode, settings, options, web=web_server
            )

    # --LAUNCH BAYESIAN OPTIMIZATION;
    elif options.bayesian_optimization:
        exit("Bayesian method is deprecated.")

    deltatime = datetime.datetime.now() - markzero_time
    print("Run took %i seconds." % deltatime.seconds)
    if options.spawn_web:
        print('Statistics info server still runs...')


