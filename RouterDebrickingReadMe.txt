#How to debrick Router
#Use at your own risk

#References
#Refer to https://forum.dd-wrt.com/phpBB2/viewtopic.php?t=62998 to build a serial cable
#and reflashing https://forum.dd-wrt.com/phpBB2/viewtopic.php?t=316814
#https://www.raspberrypi.org/documentation/usage/gpio/

#Enable GPIO Serial Port
#run the following command and enable the serial port
raspi-config

#Enable Serial port

#Reboot the pi
sudo reboot

#Find the serial port, the builtin port is /dev/ttyAMA0
#Run the following command
ls /dev/tty*

#You should have seen /dev/ttyAMA0 near the end of the list

#Install TFTP client and minicom
sudo apt-get install tftp minicom

#Setup static IP with /etc/dhcpcd.conf because the GUI used
#server of 192.168.1.255
sudo nano /etc/dhcpcd.conf

#Then inside the editor use the arrow key to go to the bottom
#type the following

interface eth0
static ip_address=192.168.1.2/24
static routers=192.168.1.1

#Press Ctrl-X and when asked to save press enter to save

#Reboot to save changes
reboot

#Run minicom substitute your serial device
minicom -b 115200 -o -D "/dev/ttyAMA0"

#Start of flashing
#if you are not able to catch something in time then
#you can restart from here.

#Make sure you use the reset button to reset NVRAM before
#starting

#When powering on the router press and hold Ctrl-C until
#You see
CFE> ^C

#Erase nvram
nvram erase

#Reboot then press and hold Ctrl-C again
reboot

#Double check that the router is set to
#ip address of 192.168.1.1 by typing the following
ifconfig

#Maksure you can ping your router

#Then type the following into one terminal but do not 
#press enter on the last line.
#Make sure you are in the same directory as your firmware
#substitute your firmware name
tftp
binary
put e2000.bin

#Switch back to the minicom terminal and type the following
flash -ctheader : flash1.trx

#quickly switch to the other terminal where you have 
#tftp setup and press enter

