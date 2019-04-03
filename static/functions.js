var canvas, panel, chart;
var socket;
var welcomeHidden = false;
var clearData = false;
var snaConfig;

window.onload = function() {
	panel = document.getElementById("panel");
	canvas = document.getElementById("canvas");

	chart = new CanvasChart({
		canvasId: 'canvas',
		margin: { top: 30, left: 50, right: 50, bottom: 30 }
	});

	socket = io.connect('http://' + document.domain + ':' + location.port);

	socket.on('config', function(data) {
		clearData = true;
		snaConfig = data;

		chart.setRelItems(null);
		document.getElementById("setRelBtn").value = "Set relative";

		document.getElementById("runBtn").value = snaConfig.runMode ? "Stop" : "Run";
		document.getElementById("sampleRate").value = Math.round(snaConfig.sampleRate / 1000000);
		document.getElementById("startFreq").value = Math.round(snaConfig.startFreq / 1000000);
		document.getElementById("endFreq").value = Math.round(snaConfig.endFreq / 1000000);
		document.getElementById("numSteps").value = snaConfig.numSteps;

		if (snaConfig.runMode==1) { //restart sweep
			snaConfig.runMode = 2;
			socket.emit('config', snaConfig);
		}
	});

	socket.on('sweepStart', function(data) {
		if (clearData) {
			hideWelcome();

			chart.init(data.freqMin, data.freqStep, data.stepCnt);
			clearData = false;
		}

		//console.log(data);
	});

	socket.on('data', function(data) {
		if (snaConfig.runMode==0)
			return;

		if (data.y instanceof Array)
			chart.setItems(data.x, data.y);
		else
			chart.setItem(data.x, data.y);
	});
}

function hideWelcome() {
	if (welcomeHidden)
		return;

	welcomeHidden = true;
	document.getElementById("welcome").style.display = "none";
	onResize();
}

function btnClick(el) {
	if (el.id=="exportImageBtn") {
		window.open(canvas.toDataURL('image/png'));
		return;
	}

	if (el.id=="exportCSVBtn") {
		var data = chart.getItems();
		var xRange = chart.getXRange();
		var csvContent = "data:text/csv;charset=utf-8,";

		for (var i=0;i<data.length;i++)
			csvContent += ((xRange.min + i*xRange.step)/1000000).toFixed(2)+","+data[i]+"\n";

		window.open(encodeURI(csvContent));
		return;
	}

	if (el.id=="setRelBtn") {
		if (el.value=="Set relative") {
			chart.setRelItems(chart.getItems());
			el.value = "Cancel relative";
		}
		else {
			chart.setRelItems(null);
			el.value = "Set relative";
		}

		if (snaConfig.runMode==1)
			snaConfig.runMode = 2;

		clearData = true;
	}
	else if (el.id=="runBtn") {
		var sampleRateInput = document.getElementById("sampleRate");
		var startFreqInput = document.getElementById("startFreq");
		var endFreqInput = document.getElementById("endFreq");
		var numStepsInput = document.getElementById("numSteps");

		if (snaConfig.runMode==0) {
			var sampleRate = Math.round(sampleRateInput.value);
			var startFreq = Math.round(startFreqInput.value);
			var endFreq = Math.round(endFreqInput.value);
			var numSteps = Math.round(numStepsInput.value);

			if (!validateInputRange(startFreq, endFreq, numSteps))
				return;

			snaConfig.sampleRate = sampleRate * 1000000;
			snaConfig.startFreq = startFreq * 1000000;
			snaConfig.endFreq = endFreq * 1000000;
			snaConfig.numSteps = numSteps;

			clearData = true;
			snaConfig.runMode = 1;
		}
		else {
			snaConfig.runMode = 0;
			chart.hideSweepCursor();
		}

		sampleRateInput.disabled = snaConfig.runMode==1;
		startFreqInput.disabled = snaConfig.runMode==1;
		endFreqInput.disabled = snaConfig.runMode==1;
		numStepsInput.disabled = snaConfig.runMode==1;

		el.value = snaConfig.runMode!=0 ? "Stop" : "Run";
	}
	
	socket.emit('config', snaConfig);
}

function onResize() {
	canvas.width = document.body.offsetWidth  - panel.offsetWidth;
	canvas.height = document.body.offsetHeight;
	chart.render();
}

function setCursorMode() {
	var cursorMode = parseInt(document.getElementById("cursoreMode").value);
	var showCutoff = document.getElementById("showCutoff").checked;
	var cutoffRange = Math.round(document.getElementById("cutoffRange").value);

	if (cutoffRange<1) {
		alert("The cutoff value must be greater then 0.");
		return;
	}

	chart.setCursorMode(cursorMode, showCutoff, cutoffRange);
}

function setYMode(e) {
	chart.setYMode(parseInt(e.value));
}

function validateInputRange(startFreq, endFreq, numSteps) {
	if (startFreq>endFreq) {
		alert("The end frequency must be less then or equal to the start frequency.");
		return false;
	}

	if (startFreq<10) {
		alert("The start frequency must be greater then or equal to 10MHz.");
		return false;
	}
	else if (startFreq>3500) {
		alert("The start frequency must be less then or equal to 3500MHz.");
		return false;
	}

	if (endFreq<10) {
		alert("The end frequency must be greater then or equal to 10MHz.");
		return false;
	}
	else if (endFreq>3500) {
		alert("The end frequency must be less then or equal to 3500MHz.");
		return false;
	}

	if (numSteps<2) {
		alert("The step count must be greater then or equal to 2.");
		return false;
	}
	else if (numSteps>1000) {
		alert("The step count must be less then or equal to 1000.");
		return false;
	}

	return true;
}