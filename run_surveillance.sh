#!/bin/bash
source ~/.profile
workon cv
cd /home/pi/pi_surveillance/


#while :
#do
	python /home/pi/pi_surveillance/pi_surveillance.py --conf /home/pi/pi_surveillance/conf.json
#done
