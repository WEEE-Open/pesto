# P.E.S.T.O.
Progetto di Erase Smart con Taralli Olistici

Hard disk SMART data checker, cleaner and system image loader.  
Successor of [Turbofresa](https://github.com/WEEE-Open/turbofresa) and [redeemer](https://github.com/WEEE-Open/redeemer).

Is constituted by:
- B.A.S.I.L.I.C.O. "Badblocks Asincrono Smart Incredibile Lancio Istantaneo di Cannoli Olistico", the server
- P.I.N.O.L.O. "Procacciatore di Informazioni Notevoli e Operazioni Laboriose Online", the client

## Functioning
PESTO is a utility software that allows you to make some operations on hard disks or SSDs, like:
- ERASE: Wipe all data on the selected drive.
- SMART: Check SMART data of the selected drive to give an estimate of the operating status of the device.
- CANNOLO: Load an operating system image on the selected drive.
- LOAD TO TARALLO: Utility that can communicate with TARALLO, sending all the necessary data to add the selected device to the inventory.  

`pinolo.py` is the user interface of the software with which the user can perform all the operations on the drives. This program by itself will be useless if not coupled with the server `basilico.py`. This one is the heart of PESTO: it performs all the commands that the user send to him, constantly sending back informations to the client that shows them to the user in a more human friendly way.

**It's highly discouraged to use the client outside a local network for security reasons.**  
There is no authentication and no encryption of any message.

## Screenshots  

![image](https://user-images.githubusercontent.com/39865402/130485205-2e5669df-9c13-49f7-9275-9bd141b3dec7.png)
![image](https://user-images.githubusercontent.com/39865402/130485454-2e14848d-56b5-45ac-926d-e891d3972e65.png)
![image](https://user-images.githubusercontent.com/39865402/130485478-73a0e3ff-87fa-46aa-8e4e-d20f46d6bad1.png)

## Client Installation
To install the client, open a terminal and execute the following commands:

1. `git clone https://github.com/WEEE-Open/pesto.git`
2. `cd pesto`
3. In program folder: `./INSTALL.sh`

PINOLO installs its dependencies automatically.  
If you need to do it manually:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements_client.txt
```

## Server Installation

To install the server in a remote machine:
1. `git clone https://github.com/WEEE-Open/pesto.git`
2. `cd pesto`
3. `python -m venv venv`
4. `source venv/bin/activate`
5. `pip install -r requirements_server.txt`
6. In program folder: `./basilico.py`

To update dependencies: ` pip install --upgrade -r requirements_server.txt`

### Server configuration

The server parses configuration in this order:

1. `/etc/basilico.conf`
2. `~/.conf/WEEE-Open/basilico.conf`
3. `.env` in the same directory as the script
4. Environment variables

The configuration file is a list of environment variables, here's an example:

```bash
# IP where the server listens, 127.0.0.1 by default, use 0.0.0.0 to listen on all interfaces
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
# Tarallo token, default none. This is an example token.
TARALLO_TOKEN=yoLeCHmEhNNseN0BlG0s3A:ksfPYziGg7ebj0goT0Zc7pbmQEIYvZpRTIkwuscAM_k
# If true, no destructive actions will be performed: no badblocks, no trimming, no cannolo. Default false.
TEST_MODE=1
```

## Credits and license

<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<div>Icons made by <a href="https://roundicons.com/" title="Roundicons">Roundicons</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<a href='https://www.freepik.com/vectors/background'>Background vector created by starline - www.freepik.com</a>

Everything else licensed as in the LICENSE file.
