#!/bin/bash

FOLDER_NAME=$(basename "$PWD")
CURRENT_DIR=$(pwd)

BLACK=0
RED=1
GREEN=2
BLUE=4
WHITE=7

tput setab $BLUE
tput setaf $BLACK
echo "                                                                               "
echo "This script will remove PESTO on your system, would you like to proceed? (y/N)"
echo "                                                                               "
tput sgr0

read CONFIRM

if [[ "$CONFIRM" != 'y' && "$CONFIRM" != 'Y' && "$CONFIRM" = "" ]]; then
  tput setab $RED
  tput setaf $BLACK
  echo "                                     "
  echo "Aborted uninstall."
  echo "Press enter to quit ..."
  echo "                                     "
  tput sgr0
  read ASD
  exit 1
fi

if [[ "$CURRENT_DIR" != "/opt/pesto" ]]; then
  tput setab $RED
  tput setaf $BLACK
  echo "                                     "
  echo "Aborted uninstall. Wrong folder. Terminating ..."
  echo "Press enter to quit ..."
  echo "                                     "
  tput sgr0
  read ASD
  exit 1
fi

echo "Removing files ..."

sudo rm -r $CURRENT_DIR
sudo rm /usr/share/applications/basilico.desktop
sudo rm /usr/share/applications/pinolo.desktop
sudo rm /usr/share/applications/uninstall_pinolo.desktop
sudo rm /etc/systemd/system/basilico.service

echo "Updating systemd ..."
sudo systemctl daemon-reload

tput setaf $BLACK
tput setab $GREEN
echo "                                                                                      "
echo "Uninstall completed succsessfully!"
echo "Press enter to quit ..."
echo "                                                                                      "
tput sgr0

read ASD
