#!/bin/bash

FOLDER_NAME=$(basename "$PWD")
CURRENT_DIR=$(pwd)
USERNAME=$(whoami)

BLACK=0
RED=1
GREEN=2
BLUE=4
WHITE=7

tput setab $BLUE
tput setaf $BLACK
echo "                                                                               "
echo "This script will install PESTO on your system, would you like to proceed? (y/N)"
echo "                                                                               "
tput sgr0

read CONFIRM

if [[ "$CONFIRM" != 'y' && "$CONFIRM" != 'Y' && "$CONFIRM" = "" ]]; then
  tput setab $RED
  tput setaf $BLACK
  echo "                                     "
  echo "Installation aborted. Terminating ..."
  echo "                                     "
  tput sgr0
  exit 1
fi

echo "Moving files in working directories ..."

sudo cp -r $CURRENT_DIR /opt/

sudo cp /opt/$FOLDER_NAME/desktop_files/basilico.desktop /usr/share/applications/
sudo cp /opt/$FOLDER_NAME/desktop_files/pinolo.desktop /usr/share/applications/
sudo cp /opt/$FOLDER_NAME/desktop_files/uninstall_pinolo.desktop /usr/share/applications/
sudo cp /opt/$FOLDER_NAME/basilico.service /etc/systemd/system/

echo "Generating python virtual environment ..."

sudo python -m venv /opt/$FOLDER_NAME/venv
sudo chown -R $USERNAME:$USERNAME /opt/pesto
source /opt/$FOLDER_NAME/venv/bin/activate
pip install -r /opt/$FOLDER_NAME/requirements_client.txt
pip install -r /opt/$FOLDER_NAME/requirements_server.txt
deactivate

echo "Updating systemd services ..."
sudo systemctl daemon-reload

tput setaf $BLACK
tput setab $GREEN
echo "                                                                                      "
echo "Installation completed succsessfully! Search for PINOLO in your applications launcher."
echo "                                                                                      "
tput sgr0
