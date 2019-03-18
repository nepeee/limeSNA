# limeSNA
This is a Scalar Network Analyzer program for the LimeSDR mini.
The python code is based on the pyLMS7002Soapy SNA example. I optimized the original code to improve the speed and added a html/javascript based GUI to make it easier to use.
For a 400-500MHz sweep with 200 data points(10 point/5MHz), the sweep time is about 17sec. The slowest part of the code currently is the tx/rx tuning(sdr.txRfFreq = xy).

![Demo image](https://github.com/nepeee/limeSNA/blob/master/demo.png)

Dependencies
- pyLMS7002Soapy Python package: https://github.com/myriadrf/pyLMS7002Soapy
- numpy (pip)
- flask (pip)
- flask_socketio (pip)
- webbrowser (pip)
- gevent (pip)
- gevent-websocket (pip)

How to use:
Install all the dependencies and run the code from a terminal with the following command:
python sna.py
After the radio is ready to use, the program starts a new web browser with the UI. Press the run button to start the frequeny sweep. For relative("calibrated") measurements wait a full sweep and then press the "Set relative" button.
