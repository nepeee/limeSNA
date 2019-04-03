from __future__ import print_function
import numpy as np
from pyLMS7002Soapy import *
from matplotlib.pyplot import *

class MultiToneSweeper:
	sampleCnt = 5000
	radio = None
	rxStream = None
	txStream = None
	txSamples = None
	txSamplesNumStep = None
	sampleRate = None
	aborted = False
	events = None

	def __init__(self, radio, sampleRate, rxGain, txGain, events):
		self.radio = radio
		self.events = events

		self.radio.tddMode = True
		self.setGain(rxGain, txGain)
		self.rxStream = self.radio.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0], {"bufferLength": str(self.sampleCnt*10)})
		self.txStream = self.radio.sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32, [0])
		self.setSampleRate(sampleRate)

	def setSampleRate(self, sampleRate):
		sampleRate = float(sampleRate)

		if (self.sampleRate==sampleRate):
			return

		if (self.sampleRate is not None):
			self.radio.sdr.deactivateStream(self.txStream)
			self.radio.sdr.deactivateStream(self.rxStream)

		self.radio.txNCOFreq = 0
		self.radio.cgenFrequency = sampleRate * 8
		self.radio.rxBandwidth = int(sampleRate * 1.5)
		self.radio.txBandwidth = int(sampleRate * 1.5)
		self.radio.rxSampleRate = sampleRate
		self.radio.txSampleRate = sampleRate

		self.sampleRate = sampleRate
		self.txSamplesNumStep = None

		self.radio.sdr.activateStream(self.rxStream)
		self.radio.sdr.activateStream(self.txStream)

	def setGain(self, rxGain, txGain):
		self.radio.rxGain = rxGain #-12, 61
		self.radio.txGain = txGain #-12, 64

	def abortSweep(self):
		self.aborted = True

	def sweep(self, snaStartFreq, snaEndFreq, snaNumSteps):
		self.aborted = False

		numSteps = snaNumSteps
		self.generateTxSamples(numSteps)
		
		txNCOStep = int(round(self.sampleRate / numSteps))
		self.events.sweepStart(snaStartFreq, txNCOStep, math.floor((snaEndFreq-snaStartFreq) / txNCOStep))

		fftStep = int(round(self.sampleCnt / numSteps))
		fftOffset = int(round(fftStep / 2))
		txRfFreq = snaStartFreq + (self.sampleRate / 2)
		snaEndFreq = snaEndFreq - (self.sampleRate / 2)

		n = 0
		brk = False
		while (True):
			print(".", end="")
			self.radio.txRfFreq = txRfFreq
			self.radio.configureAntenna(txRfFreq)

			self.radio.sdr.writeStream(self.txStream, [self.txSamples], self.txSamples.size)

			targetTime = int(self.radio.sdr.getHardwareTime() + 1e6)
			buff = self.readSamples(self.sampleCnt, targetTime)

			spect = np.fft.fft(buff)
			spect = np.fft.fftshift(spect)
			spect = spect[fftOffset::fftStep]
			pwrs = 20*np.log10(np.abs(spect) / self.sampleCnt / 2)

			self.events.sweepResult(n, pwrs.tolist())
			n += pwrs.size

			if ((txRfFreq >= snaEndFreq) or (self.aborted)):
				break

			txRfFreq += self.sampleRate

		print(" ")


	def generateTxSamples(self, numSteps):
		if (self.txSamplesNumStep==numSteps):
			return

		freqStep = int(round(self.sampleRate / numSteps))
		freqOffset = int(round(freqStep / 2))
		freqGain = 1.0 / numSteps
		txSampleCnt = self.sampleCnt * 20

		s = None
		for i in range(int(numSteps*-0.5), int(numSteps*0.5)):
			freq = freqOffset + freqStep*i;
			phaseInc = 2*math.pi*freq/self.sampleRate
			phases = np.linspace(0, txSampleCnt*phaseInc, txSampleCnt)
			s1 = freqGain * np.exp(1j * phases)

			if (s is None):
				s = s1
			else:
				s += s1

		self.txSamplesNumStep = numSteps
		self.txSamples = s.astype(np.complex64)

	def readSamples(self, nSamples, targetTimeNs):
		buff = np.zeros(nSamples, np.complex64)
		numElemsRequest = nSamples

		while numElemsRequest > 0:
			sr = self.radio.sdr.readStream(self.rxStream, [buff], nSamples)
			if (sr.timeNs>=targetTimeNs):
				numElemsRequest -= sr.ret

		return buff