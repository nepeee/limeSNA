from __future__ import print_function
import time
import math
import threading
from pyLMS7002Soapy import *
import numpy as np
from flask import Flask, request
from flask_socketio import SocketIO
import webbrowser

RUN_MODE_OFF = 0
RUN_MODE_ON = 1
RUN_MODE_UPDATE_CONFIG = 2

thread = None

snaRunMode = RUN_MODE_OFF
snaStartFreq = 400000000
snaEndFreq = 500000000
snaNumSteps = 5

app = Flask(__name__, static_url_path='/static')
socketio = SocketIO(app, async_mode='gevent')

@app.route('/')
def root():
    return app.send_static_file('index.html')

def readSamples(sdr, rxStream, nSamples):
    buff = np.zeros(nSamples, np.complex64)
    numElemsRequest = nSamples
    while numElemsRequest > 0:
        sr = sdr.sdr.readStream(rxStream, [buff], nSamples)
        numElemsRequest -= sr.ret
    return buff

def snaThread():
    global snaRunMode, snaStartFreq, snaEndFreq, snaNumSteps

    sdr = pyLMS7002Soapy(0)

    sdr.cgenFrequency = 80e6
    sdr.rxSampleRate = 5e6
    sdr.txSampleRate = 5e6
    sdr.rxBandWidth = 10e6
    sdr.txBandwidth = 10e6
    sdr.rxGain = 20
    sdr.txGain = 20

    rxStream = sdr.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0], {"bufferLength": "10000"})
    sdr.tddMode = True
    sdr.testSignalDC(0x3fff, 0x3fff)
    sdr.configureAntenna(sdr.txRfFreq)

    sdr.sdr.activateStream(rxStream)

    sampleCnt = 5000 #do not modify
    busyLoopCnt = int(sdr.rxSampleRate / 312500)+1 # 17ms

    webbrowser.open("http://127.0.0.1:55555", new=1)

    while True:
        if (snaRunMode==RUN_MODE_OFF):
            time.sleep(0.1)
            continue
        elif (snaRunMode==RUN_MODE_UPDATE_CONFIG):
            snaRunMode = RUN_MODE_ON
        
        start = time.time()

        numSteps = snaNumSteps
        txNCOStep = int(sdr.rxSampleRate / 2 / numSteps)
        txNCOOffset = int(txNCOStep / 2)
        txRfFreq = snaStartFreq + txNCOStep*numSteps - txNCOOffset
        fftStep = int(sampleCnt / 2 / numSteps)
        fftOffset = int((sampleCnt / 2) + (fftStep / 2))

        socketio.emit('sweepStart', {
            'freqMin': snaStartFreq,
            'freqStep': txNCOStep,
            'stepCnt': math.floor((snaEndFreq-snaStartFreq) / txNCOStep) + 1
        })

        n = 0
        brk = False
        while (True):
            sdr.txRfFreq = txRfFreq
            sdr.configureAntenna(sdr.txRfFreq)

            for i in range(-1*numSteps, numSteps):
                print(".", end="")
                txNCOFreq = txNCOOffset + txNCOStep*i
                sdr.txNCOFreq = txNCOFreq

                for k in range(0, busyLoopCnt): # busyloop to wait for valid samples ~17ms
                    buff = readSamples(sdr, rxStream, sampleCnt)

                spect = np.fft.fft(buff)
                spect = np.fft.fftshift(spect)
                pwr = 20*np.log10(abs(spect[fftOffset + fftStep*i]))
                
                socketio.emit('data', {
                    #'f': txRfFreq + txNCOFreq,
                    'x': n,
                    'y': pwr
                })

                if ((txRfFreq + txNCOFreq >= snaEndFreq) or (snaRunMode!=RUN_MODE_ON)):
                    brk = True
                    break

                n += 1

            print(" ")

            if (brk):
                break

            txRfFreq += sdr.rxSampleRate

        end = time.time()
        print(end - start)

@socketio.on('connect')
def connect():
    global thread, snaRunMode, snaStartFreq, snaEndFreq, snaNumSteps
    socketio.emit('config', {
        'startFreq': snaStartFreq,
        'endFreq': snaEndFreq,
        'numSteps': snaNumSteps,
        'runMode': snaRunMode
    })

@socketio.on('config')
def handle_json(json):
    global snaRunMode, snaStartFreq, snaEndFreq, snaNumSteps
    
    snaStartFreq = int(json['startFreq'])
    snaEndFreq = int(json['endFreq'])
    snaNumSteps = int(json['numSteps'])
    snaRunMode = int(json['runMode'])

if __name__ == '__main__':
    thread = threading.Thread(target=snaThread)
    thread.start()

    socketio.run(app, port=55555) #, debug=True