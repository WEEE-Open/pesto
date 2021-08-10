
# P.E.S.T.O.
Parser Estremamente Smart Tremendamente Ottimizzato

Hard disk SMART data checker, cleaner and system image loader.

![image](https://user-images.githubusercontent.com/39865402/128496857-68cf7025-24fe-4621-abca-ae62219e13ac.png)
![image](https://user-images.githubusercontent.com/39865402/128496754-393a145d-3e66-487b-8418-d654a85efd15.png)

## Installation
The software can work locally or remotely.
For the client side:
1. git clone https://github.com/WEEE-Open/pesto.git
2. sudo chmod +x pesto.py
3. In program folder: ./pesto.py  

For the server side is sufficient to place the pesto_server.py file in the working directory and execute it.

## Functioning
The program pesto.py (or pesto_noCmd.pyw to hide console) is a GUI software that can do all the supported operations on the drives of the local machine and can send commands to the "remote" server (another machine in the same local network) that can do the same operations.

The program pesto_server.py is the server side software that can get commands by a client in the same local network to do all the supported operations on the server's drives.

**It's highly discouraged to use the client outside a local network for security reasons.**

## Supported operations
* Pialla disco: Wipe all data on the selected drive
* Smart: Check SMART data of the selected drive and give an indication of the overall status of the device
* Cannolo: Load a system image to the selected drive. The system image can be set in the settings panel


<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<div>Icons made by <a href="https://roundicons.com/" title="Roundicons">Roundicons</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
