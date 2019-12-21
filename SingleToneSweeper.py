from __future__ import print_function
import math
import numpy as np
from pyLMS7002Soapy import pyLMS7002Soapy as pyLMSS
from scipy import signal

class SingleToneSweeper:
	sampleCnt = 4096
	radio = None
	rxStream = None
	sampleRate = None
	bandWidth = None
	aborted = False
	events = None

	def __init__(self, radio, events):
		self.radio = radio
		self.events = events

		self.radio.tddMode = True
		self.radio.testSignalDC(0x3fff, 0x3fff)
		self.rxStream = self.radio.sdr.setupStream(pyLMSS.SOAPY_SDR_RX, pyLMSS.SOAPY_SDR_CF32, [0], {"bufferLength": str(self.sampleCnt*10)})

	def setSampleRate(self, sampleRate):
		sampleRate = float(sampleRate)

		if (self.sampleRate==sampleRate):
			return

		if (self.sampleRate is not None):
			self.radio.sdr.deactivateStream(self.rxStream)

		self.radio.txNCOFreq = 0
		self.radio.cgenFrequency = sampleRate * 8
		self.radio.rxBandwidth = round(sampleRate * 1.25)
		self.radio.txBandwidth = round(sampleRate * 1.25)
		self.radio.rxSampleRate = sampleRate
		self.radio.txSampleRate = sampleRate
		self.sampleRate = sampleRate
		self.bandWidth = sampleRate #round(sampleRate*0.5)

		self.radio.sdr.activateStream(self.rxStream)

	def setGain(self, rxGain, txGain):
		self.radio.rxGain = rxGain #-12, 61
		self.radio.txGain = txGain #-12, 64

	def abortSweep(self):
		self.aborted = True

	def sweep(self, snaStartFreq, snaEndFreq, snaNumSteps):
		self.aborted = False

		numSteps = math.ceil(snaNumSteps / 2) * 2
		txNCOStep = round(self.bandWidth / numSteps)
		txNCOOffset = round(txNCOStep / 2)
		txNCOFreqStart = txNCOStep*(numSteps/2) - txNCOOffset
		txRfFreq = snaStartFreq + txNCOFreqStart
		txNCOFreqStart *= -1

		self.events.sweepStart(snaStartFreq, txNCOStep, math.floor((snaEndFreq-snaStartFreq) / txNCOStep) + 1)

		n = 0
		brk = False
		while (True):
			fftIndex = 0 #round(numSteps/2)
			txNCOFreq = txNCOFreqStart

			self.radio.txNCOFreq = txNCOFreq #pretune nco to avoid loss of samples
			self.radio.txRfFreq = txRfFreq
			self.radio.configureAntenna(txRfFreq)

			for i in range(0, numSteps):
				print(".", end="", flush=True)

				self.radio.txNCOFreq = txNCOFreq
				targetTime = self.radio.sdr.getHardwareTime() + 1e6
				buff = self.readSamples(self.sampleCnt, targetTime)

				fft = signal.welch(buff, 1.0, 'flattop', numSteps, scaling='spectrum', return_onesided=False, detrend=False)
				fft = np.fft.fftshift(fft[1])
				pwr = 10*np.log10(fft[fftIndex])

				self.events.sweepResult(n, pwr)

				if ((txRfFreq + txNCOFreq >= snaEndFreq) or (self.aborted)):
					brk = True
					break

				txNCOFreq += txNCOStep
				fftIndex += 1
				n += 1

			print(" ")

			if (brk):
				break

			txRfFreq += self.bandWidth

	def readSamples(self, nSamples, targetTimeNs):
		buff = np.zeros(nSamples, np.complex64)
		numElemsRequest = nSamples

		while numElemsRequest > 0:
			sr = self.radio.sdr.readStream(self.rxStream, [buff], nSamples)
			if (sr.timeNs>=targetTimeNs):
				numElemsRequest -= sr.ret

		return buff