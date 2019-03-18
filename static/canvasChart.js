function CanvasChart(dataObj) {
    var dataPoints = null;
    var dataLength = 0;
    var sweepPos;

    var cursor = {//0 mouse, 1 max hold, 2 min hold
        mode: 0,
        x: 0,
        y: 0
    };

    var xMin, xRange, xMax;
    var yMin, yRange, yMax;

    var vxMin, vxRange, vxMax, vxStep;
    var vyMin, vyRange, vyMax;
    var vyMinIndex, vyMaxIndex;

    var xRatio, yRatio;

    var margin = dataObj.margin;

    var canvas = document.getElementById(dataObj.canvasId);
    var ctx = canvas.getContext("2d");
    ctx.font = '10pt Calibri';

    canvas.addEventListener("mousemove", setCursorPos);

    function render() {
        if (dataPoints==null)
            return;

        xMin = margin.left;
        xMax = canvas.width - margin.right;
        xRange = xMax - xMin;

        yMin = margin.top;
        yMax = canvas.height - margin.bottom;
        yRange = yMax - yMin;

        vyMin = 1000.0;
        vyMax = -1000.0;
        dataLength = dataPoints.length;
        for (var i=0;i<dataLength;i++) {
            var val = dataPoints[i];
            if (val==null)
                continue;

            if (val < vyMin) {
                vyMin = val;
                vyMinIndex = i;
            }
            if (val > vyMax) {
                vyMax = val;
                vyMaxIndex = i;
            }
        }
        vyRange = vyMax - vyMin;

        xRatio = xRange / (dataLength - 1);
        yRatio = yRange*-1 / vyRange;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        renderLinesAndLabels();
        renderData();
        renderCursors();
    };

    function renderLinesAndLabels() {
        var gradCnt = 10;

        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = '#E8E8E8'

        //v lines + text
        var xPos = xMin;
        var xInc = xRange / gradCnt;

        var val = vxMin;
        var valInc = vxRange / gradCnt;

        ctx.textBaseline = 'top';
        ctx.textAlign = 'center';
        for (var i=0;i<=gradCnt;i++) { 
            ctx.moveTo(xPos, yMin);
            ctx.lineTo(xPos, yMax);
            
            var txt = (val/1000000).toFixed(1);
            ctx.fillText(txt, xPos, yMax + 10);

            xPos += xInc;
            val += valInc;
        }

        //h lines + text
        var yPos = yMin;
        var yInc = yRange / gradCnt;

        var val = vyMax;
        var valDec = vyRange / gradCnt;

        ctx.textBaseline = 'middle';
        ctx.textAlign = 'right';
        for (var i=0;i<=gradCnt;i++) {
            ctx.moveTo(xMin, yPos);
            ctx.lineTo(xMax, yPos);

            var txt = val.toFixed(1);
            ctx.fillText(txt, xMin - 10, yPos);

            yPos += yInc;
            val -= valDec;
        }

        ctx.stroke();
        ctx.closePath();
    };

    function renderData() {
        var first = true;

        ctx.beginPath();
        ctx.strokeStyle = '#269FD6';
        ctx.lineWidth = 2;
        for (var i=0;i<dataLength;i++) {
            var yVal = dataPoints[i];
            if (yVal==null)
                continue;

            var ptX = xMin + i * xRatio;
            var ptY = yMax + (yVal - vyMin) * yRatio;

            if (first) {
                first = false;
                ctx.moveTo(ptX, ptY);
            }
            else
                ctx.lineTo(ptX, ptY);
        }

        ctx.stroke();
        ctx.closePath();
    };

    function renderCursors() {
        ctx.beginPath();
        ctx.strokeStyle = '#FFDFBA';
        ctx.lineWidth = 1;

        var ptX = xMin + sweepPos * xRatio;
        ctx.moveTo(ptX, xMin);
        ctx.lineTo(ptX, yMax);
        ctx.stroke();
        ctx.closePath();

        var ptX, ptY;
        if (cursor.mode==0) {
            ptX = cursor.x;
            ptY = cursor.y;

            if (ptX<xMin)
                ptX = xMin;
            else if (ptX>xMax)
                ptX = xMax;

            if (ptY<yMin)
                ptY = yMin;
            else if (ptY>yMax)
                ptY = yMax;
        }
        else if (cursor.mode==1) {
            ptX = xMin + vyMaxIndex * xRatio;
            ptY = canvas.height / 2;
        }
        else if (cursor.mode==2) {
            ptX = xMin + vyMinIndex * xRatio;
            ptY = canvas.height / 2;
        }

        var xIndex = Math.round((ptX - xMin) / xRatio);
        var freq = vxMin + xIndex * vxStep;
        var pwr = dataPoints[xIndex];

        ctx.beginPath();
        ctx.strokeStyle = '#000';
        ctx.textBaseline = 'center';

        var textXPos;
        if ((ptX - xMin)<100) {
            ctx.textAlign = 'left';
            textXPos = ptX + 20;
        }
        else {
            ctx.textAlign = 'right';
            textXPos = ptX - 10;
        }

        if ((cursor.mode!=0) && (pwr!=null)) {
            var bwin = getBandwidthWindow(xIndex, pwr, cursor.mode==1 ? -3 : 3);
            var xStart = xMin + bwin.startIndex * xRatio;
            var xWidth = (xMin + bwin.endIndex * xRatio) - xStart;
            if (xWidth>0) {
                ctx.globalAlpha = 0.05;
                ctx.fillRect(xStart, yMin, xWidth, yRange);
                ctx.globalAlpha = 1;

                var freqMin = vxMin + bwin.startIndex * vxStep;
                var freqMax = vxMin + bwin.endIndex * vxStep;
                ctx.fillText((freqMin/1000000).toFixed(2)+"MHz", textXPos, ptY + 15);
                ctx.fillText((freqMax/1000000).toFixed(2)+"MHz", textXPos, ptY + 24);
            }
        }

        ctx.moveTo(ptX, yMin);
        ctx.lineTo(ptX, yMax);

        if (pwr!=null) {
            ctx.fillText(pwr.toFixed(1)+"dB", textXPos, ptY - 6);
            ctx.fillText((freq/1000000).toFixed(2)+"MHz", textXPos, ptY + 6);
        }
        else
            ctx.fillText((freq/1000000).toFixed(2)+"MHz", textXPos, ptY);

        ctx.stroke();
        ctx.closePath();
    }

    function getBandwidthWindow(valIndex, targetVal, range) {
        var startIndex = null;
        var endIndex = null;
        var np = valIndex;
        var nn = valIndex;

        while (true) {
            if (np>dataLength-1)
                endIndex = dataLength - 1;
            else
                np++;
            
            if (nn<1)
                startIndex = 0;
            else
                nn--;

            if (range<0) {
                if ((endIndex==null) && (dataPoints[np]<targetVal+range))
                    endIndex = np - 1;

                if ((startIndex==null) && (dataPoints[nn]<targetVal+range))
                    startIndex = nn + 1;
            }
            else {
                if ((endIndex==null) && (dataPoints[np]>targetVal+range))
                    endIndex = np - 1;

                if ((startIndex==null) && (dataPoints[nn]>targetVal+range))
                    startIndex = nn + 1;                
            }

            if ((startIndex!=null) && (endIndex!=null))
                break;
        }

        return {
            startIndex: startIndex,
            endIndex: endIndex
        };
    }

    function init(xMin, xStep, xStepCnt) {
        dataPoints = Array();
        for (var i=0;i<xStepCnt;i++)
            dataPoints[i] = null;

        vxStep = xStep;
        vxMin = xMin;
        vxRange = vxStep * (xStepCnt-1);
        vxMax = xMin + vxRange;
    }

    function setItem(index, val) {
        if (dataPoints==null)
            return;

        dataPoints[index] = val;
        sweepPos = index;

        render();
    }

    function getData() {
        return dataPoints.slice(0);
    }

    function setCursorMode(mode) {
        cursor.mode = mode;
        render();
    }

    function setCursorPos(e) {
        if (cursor.mode==0) {
            var rect = e.target.getBoundingClientRect();
            cursor.x = e.clientX - rect.left;
            cursor.y = e.clientY - rect.top;
            
            render();
        }
    }

    return {
        init: init,
        setItem: setItem,
        getData: getData,
        setCursorMode: setCursorMode,
        render: render
    };
};
