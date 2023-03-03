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

## Installation

To install pesto in the system:

```bash
git clone https://github.com/WEEE-Open/pesto.git
cd pesto
./INSTALL.sh
```

The script installs the software in `/opt/pesto` and generates the virtual environment with the necessary dependencies. 

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

Immediately after the installation, you may need to copy the `.env.example` file in the same path as `.env`.
Then you can edit the `.env` file to set your configuration. Generally, the default configuration is good but to use
TARALLO features you have to set the TARALLO_URL and TARALLO_TOKEN environment variables.

## Screenshots  

![Screenshot_20220923_104046](https://user-images.githubusercontent.com/39865402/191923572-3fef4ec4-a5c9-4ff8-aad2-2f5ef9c0667a.png)
![Screenshot_20220923_104143](https://user-images.githubusercontent.com/39865402/191923577-c5d0baf1-5a94-48c0-9aaf-6b28f8304274.png)
![Screenshot_20220923_104157](https://user-images.githubusercontent.com/39865402/191923589-4d1f9975-00e5-401c-bddd-434eb7f06396.png)
![Screenshot_20220923_104400](https://user-images.githubusercontent.com/39865402/191923858-6c130e19-265c-4d15-8228-95e21658f04c.png)



## Credits and license

<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<div>Icons made by <a href="https://roundicons.com/" title="Roundicons">Roundicons</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>  
<a href='https://www.freepik.com/vectors/background'>Background vector created by starline - www.freepik.com</a>

Everything else licensed as in the LICENSE file.
