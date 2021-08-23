
# P.E.S.T.O.
Progetto di Erase Smart con Taralli Olistici

Hard disk SMART data checker, cleaner and system image loader.  
Successor of [Turbofresa](https://github.com/WEEE-Open/turbofresa) and [redeemer](https://github.com/WEEE-Open/redeemer).

Is constituted by:
- B.A.S.I.L.I.C.O. "Badblocks Asincrono Smart Incredibile Lancio Istantaneo di Cannoli Olistico" --> Server
- P.I.N.O.L.O. "Procacciatore di Informazioni Notevoli e Operazioni Laboriose Online"  --> Client

## Installation
The software can work locally or remotely.
For the client side:
1. `git clone https://github.com/WEEE-Open/pesto.git`
2. `sudo chmod +x pesto.py`
3. In program folder: `./pesto.py` or `./basilico.py`

PEsto installs its dependencies automatically, while for basilico you'll need:

```bash
pip install -r requirements_server.txt
```

### Server configuration

Configuration is read in this order:

1. /etc/basilico.conf
2. ~/.conf/WEEE-Open/basilico.conf
3. env
4. Environment variables

The configuration file is a list of environment variables, here's an example:

```bash
# IP where the server listens, 127.0.0.1 by default
IP=0.0.0.0
# Port, default 1030.
PORT=1030
# Log level: DEBUG, INFO, WARNING, ERROR. Default INFO.
LOGLEVEL=DEBUG
# Start as a daemon or a normal process, boolean, not very well tested. Default false.
DAEMONIZE=0
# Lock file for the daemon. Default /var/run/basilico.pid.
LOCKFILE_PATH=/var/run/basilico.pid
# Tarallo URL for pytarallo. Default none (tarallo will not be used)
TARALLO_URL=http://127.0.0.1:8080
# Tarallo token, default none.
TARALLO_TOKEN=yoLeCHmEhNNseN0BlG0s3A:ksfPYziGg7ebj0goT0Zc7pbmQEIYvZpRTIkwuscAM_k
# If true, no destructive actions will be performed: no badblocks, no trimming, no cannolo. Default false.
TEST_MODE=1
```

## Functioning
The program pesto.py (or pesto_noCmd.pyw to hide console) is a GUI software that can do all the supported operations on the drives of the local machine and can send commands to the "remote" server (another machine in the same local network) that can do the same operations.

The program pesto_server.py is the server side software that can get commands by a client in the same local network to do all the supported operations on the server's drives.

**It's highly discouraged to use the client outside a local network for security reasons.**

### Supported operations
* Pialla disco: Wipe all data on the selected drive
* Smart: Check SMART data of the selected drive and give an indication of the overall status of the device
* Cannolo: Load a system image to the selected drive. The system image can be set in the settings panel

## Screenshots  

![image](https://user-images.githubusercontent.com/39865402/130485205-2e5669df-9c13-49f7-9275-9bd141b3dec7.png)
![image](https://user-images.githubusercontent.com/39865402/130485454-2e14848d-56b5-45ac-926d-e891d3972e65.png)
![image](https://user-images.githubusercontent.com/39865402/130485478-73a0e3ff-87fa-46aa-8e4e-d20f46d6bad1.png)

<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<div>Icons made by <a href="https://roundicons.com/" title="Roundicons">Roundicons</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<a href='https://www.freepik.com/vectors/background'>Background vector created by starline - www.freepik.com</a>
