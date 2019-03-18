var canvas, panel, chart;
var socket;
var welcomeHidden = false;
var clearData = false;
var snaConfig;
var relData = null;

window.onload = function() {
	panel = document.getElementById("panel");
	canvas = document.getElementById("canvas");

	chart = new CanvasChart({
		canvasId: 'canvas',
		margin: { top: 50, left: 50, right: 50, bottom: 50 }
	});

	socket = io.connect('http://' + document.domain + ':' + location.port);

	socket.on('config', function(data) {
		clearData = true;
		snaConfig = data;
		relData = null;

		document.getElementById("runBtn").value = snaConfig.runMode ? "Stop" : "Run";
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
		if (relData!=null)
			chart.setItem(data.x, data.y - relData[data.x]);
		else
			chart.setItem(data.x, data.y);

		//console.log(data);
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
	if (el.id=="setRelBtn") {
		if (relData==null) {
			relData = chart.getData();
			el.value = "Cancel relative";
		}
		else {
			relData = null;
			el.value = "Set relative";
		}

		return;
	}

	if (el.id=="runBtn") {
		if (snaConfig.runMode==0)
			snaConfig.runMode = 1;
		else
			snaConfig.runMode = 0;

		el.value = snaConfig.runMode!=0 ? "Stop" : "Run";
	}
	else if (el.id=="setRangeBtn") {
		relData = null;
		if (snaConfig.runMode==1)
			snaConfig.runMode = 2;
	}

	var startFreq = Math.round(document.getElementById("startFreq").value);
	var endFreq = Math.round(document.getElementById("endFreq").value);
	var numSteps = Math.round(document.getElementById("numSteps").value);

	if (!validateInputRange(startFreq, endFreq, numSteps))
		return;

	snaConfig.startFreq = startFreq * 1000000;
	snaConfig.endFreq = endFreq * 1000000;
	snaConfig.numSteps = numSteps;

	clearData = true;

	socket.emit('config', snaConfig);
}

function onResize() {
	canvas.width = document.body.offsetWidth;
	canvas.height = document.body.offsetHeight - panel.offsetHeight;
	chart.render();
}

function setCursorMode(e) {
	chart.setCursorMode(parseInt(e.value));
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

	if (numSteps<1) {
		alert("The step count must be greater then or equal to 1.");
		return false;
	}
	else if (numSteps>1000) {
		alert("The step count must be less then or equal to 1000.");
		return false;
	}

	return true;
}