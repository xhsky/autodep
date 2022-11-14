#!/bin/bash

setstatus softmode
sudo ./main.py -t stop
sleep 100
sudo rm -rf /data/dream/;sudo rm -rf /dream;sudo rm -f /etc/profile.d/jdk.sh;sudo rm -f /etc/profile.d/mysql.sh;sudo rm -f /etc/my_plugin.cnf;sudo rm -f /etc/my_client.cnf;sudo rm -f /etc/my.cnf;sudo rm -f /etc/rc.local;sudo rm -rf /opt/python3/


