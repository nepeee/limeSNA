from __future__ import print_function
import time
import threading
from pyLMS7002Soapy import pyLMS7002Soapy as pyLMSS
from flask import Flask, request
from flask_socketio import SocketIO
import webbrowser

from SingleToneSweeper import SingleToneSweeper

class SNA:
    RUN_MODE_OFF = 0
    RUN_MODE_ON = 1
    RUN_MODE_UPDATE_CONFIG = 2

    thread = None
    socketio = None

    sweeper = None
    snaRunMode = RUN_MODE_OFF
    snaSampleRate = 20e6
    snaStartFreq = 400e6
    snaEndFreq = 500e6
    snaNumSteps = 40
    snaRxGain = 20
    snaTxGain = 20

    def __init__(self):
        app = Flask(__name__, static_url_path='/static')
        self.socketio = SocketIO(app, async_mode='gevent')

        thread = threading.Thread(target=self.snaThread)
        thread.start()

        @app.route('/')
        def root():
            return app.send_static_file('index.html')

        @self.socketio.on('connect')
        def connect():
            self.socketio.emit('config', {
                'sampleRate': self.snaSampleRate,
                'startFreq': self.snaStartFreq,
                'endFreq': self.snaEndFreq,
                'numSteps': self.snaNumSteps,
                'rxGain': self.snaRxGain,
                'txGain': self.snaTxGain,
                'runMode': self.snaRunMode
            })

        @self.socketio.on('config')
        def handle_json(json):
            self.snaSampleRate = int(json['sampleRate'])
            self.snaStartFreq = int(json['startFreq'])
            self.snaEndFreq = int(json['endFreq'])
            self.snaNumSteps = int(json['numSteps'])
            self.snaRxGain = int(json['rxGain'])
            self.snaTxGain = int(json['txGain'])
            self.snaRunMode = int(json['runMode'])

            if ((self.snaRunMode!=self.RUN_MODE_ON) and (self.sweeper is not None)):
                self.sweeper.abortSweep()

        self.socketio.run(app, port=55555)

    def sweepStart(self, startFreq, freqStep, stepCnt):
        self.socketio.emit('sweepStart', {
            'freqMin': startFreq,
            'freqStep': freqStep,
            'stepCnt': stepCnt
        })

    def sweepResult(self, index, pwr):
        self.socketio.emit('data', {
            'x': index,
            'y': pwr
        })
        self.socketio.sleep(0)

    def snaThread(self):
        radio = pyLMSS.pyLMS7002Soapy(0)
        self.sweeper = SingleToneSweeper(radio, self)
        webbrowser.open("http://127.0.0.1:55555", new=1)

        while True:
            if (self.snaRunMode==self.RUN_MODE_OFF):
                time.sleep(0.1)
                continue
            elif (self.snaRunMode==self.RUN_MODE_UPDATE_CONFIG):
                self.snaRunMode = self.RUN_MODE_ON
          
            start = time.time()

            self.sweeper.setGain(self.snaRxGain, self.snaTxGain)
            self.sweeper.setSampleRate(self.snaSampleRate)
            self.sweeper.sweep(self.snaStartFreq, self.snaEndFreq, self.snaNumSteps)

            end = time.time()
            print(end - start)

if __name__ == '__main__':
    SNA()