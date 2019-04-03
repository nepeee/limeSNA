from __future__ import print_function
import math
import numpy as np
from pyLMS7002Soapy import *

class SingleToneSweeper:
	sampleCnt = 5000
	radio = None
	rxStream = None
	sampleRate = None
	bandWidth = None
	aborted = False
	events = None

	def __init__(self, radio, sampleRate, rxGain, txGain, events):
		self.radio = radio
		self.events = events

		self.radio.tddMode = True
		self.radio.testSignalDC(0x3fff, 0x3fff)
		self.setGain(rxGain, txGain)
		self.rxStream = self.radio.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0], {"bufferLength": str(self.sampleCnt*10)})
		self.setSampleRate(sampleRate)

	def setSampleRate(self, sampleRate):
		sampleRate = float(sampleRate)

		if (self.sampleRate==sampleRate):
			return

		if (self.sampleRate is not None):
			self.radio.sdr.deactivateStream(self.rxStream)

		self.radio.txNCOFreq = 0
		self.radio.cgenFrequency = sampleRate * 8
		self.radio.rxBandwidth = int(sampleRate * 1.5)
		self.radio.txBandwidth = int(sampleRate * 1.5)
		self.radio.rxSampleRate = sampleRate
		self.radio.txSampleRate = sampleRate

		self.sampleRate = sampleRate
		self.bandWidth = sampleRate

		self.radio.sdr.activateStream(self.rxStream)

	def setGain(self, rxGain, txGain):
		self.radio.rxGain = rxGain #-12, 61
		self.radio.txGain = txGain #-12, 64

	def abortSweep(self):
		self.aborted = True

	def sweep(self, snaStartFreq, snaEndFreq, snaNumSteps):
		self.aborted = False

		numSteps = int(math.ceil(snaNumSteps / 2))
		txNCOStep = int(round(self.bandWidth / 2 / numSteps))
		txNCOOffset = int(round(txNCOStep / 2))
		txRfFreq = snaStartFreq + txNCOStep*numSteps - txNCOOffset

		self.events.sweepStart(snaStartFreq, txNCOStep, math.floor((snaEndFreq-snaStartFreq) / txNCOStep) + 1)

		n = 0
		brk = False
		while (True):
			self.radio.txRfFreq = txRfFreq
			self.radio.configureAntenna(txRfFreq)

			for i in range(-1*numSteps, numSteps):
				print(".", end="")
				txNCOFreq = txNCOOffset + txNCOStep*i
				self.radio.txNCOFreq = txNCOFreq

				targetTime = int(self.radio.sdr.getHardwareTime() + 1e6)
				buff = self.readSamples(self.sampleCnt, targetTime)

				spect = np.fft.fft(buff)
				spect = np.fft.fftshift(spect)
				fftIndex = int(round(((txNCOFreq + self.sampleRate / 2) / self.sampleRate) * self.sampleCnt))
				pwr = 20*np.log10(np.abs(spect[fftIndex]) / self.sampleCnt / 2)

				self.events.sweepResult(n, pwr)

				if ((txRfFreq + txNCOFreq >= snaEndFreq) or (self.aborted)):
					brk = True
					break

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