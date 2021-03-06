# USAGE
# python pi_surveillance.py --conf conf.json

# import the necessary packages
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
#import imutils
import json
import time
import os
import subprocess
import threading
import uuid

import RPi.GPIO as GPIO


class TempImage:
        def __init__(self, basePath="./", ext=".jpg"):
                # construct the file path
                self.path = "{base_path}/{rand}{ext}".format(base_path=basePath,
                rand=str(uuid.uuid4()), ext=ext)
                print self.path

        def cleanup(self):
                # remove the file
                os.remove(self.path)

def send_to_db_and_slack(tempImage, frame, dbClient, ts):
	try:
		# write the image to temporary file
		cv2.imwrite(tempImage.path, frame)

		# upload the image to Dropbox and cleanup the tempory image
		print "[UPLOAD] {}".format(ts)
		path = "{base_path}/{timestamp}.jpg".format(
	        	base_path=conf["dropbox_base_path"], timestamp=ts)
		dbClient.put_file(path, open(t.path, "rb"))
		dbUrl = dbClient.share(path, short_url=False)
		#print dbUrl['url']	
		revisedDbUrl = dbUrl['url'].replace("www.dropbox.com", "dl.dropboxusercontent.com");
		#print revisedDbUrl
		param = '\"' + revisedDbUrl+ '\"'
		#print param
		#subprocess.call(['/home/pi/process-result-slack-report/slackImage.py', '--i', param ], shell=True)
		command = '/home/pi/process-result-slack-report/slackImage.py --i "' + revisedDbUrl + '"'
		#print command
		subprocess.call(command, shell=True)
		tempImage.cleanup()
	except Exception as e:
		print e

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
	help="path to the JSON configuration file")
args = vars(ap.parse_args())

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None
pir_channel = conf["pir_channel"]

GPIO.setmode(GPIO.BOARD)
GPIO.cleanup()
GPIO.setup(pir_channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# check to see if the Dropbox should be used
if conf["use_dropbox"]:
	# connect to dropbox and start the session authorization process
	flow = DropboxOAuth2FlowNoRedirect(conf["dropbox_key"], conf["dropbox_secret"])
	#print "[INFO] Authorize this application: {}".format(flow.start())
	#authCode = raw_input("Enter auth code here: ").strip()

	# finish the authorization and grab the Dropbox client
	#(accessToken, userID) = flow.finish(authCode)
	client = DropboxClient(conf["dropbox_access_token"])
	#print "aT: " + accessToken 
	#print "uID:" + userID 
	#print "authCode:" + authCode
	print "[SUCCESS] dropbox account linked"

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.vflip = True
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print "[INFO] warming up..."
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

print "Ready..."

while true:
        GPIO.wait_for_edge(pir_channel, GPIO.BOTH)
        tempImage = TempImage()
        camera.capture(tempImage.path)
        
# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	
	GPIO.wait_for_edge(pir_channel, GPIO.BOTH)
	print "Val: %s" % GPIO.input(pir_channel)

        # grab the raw NumPy array representing the image and initialize
	# the timestamp and occupied/unoccupied text
	frame = f.array
	timestamp = datetime.datetime.now()
	text = "Occupied"

	# resize the frame, convert it to grayscale, and blur it
	#frame = imutils.resize(frame, width=500)
	#gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	#gray = cv2.GaussianBlur(gray, (21, 21), 0)

	# if the average frame is None, initialize it
	#if avg is None:
	#	print "[INFO] starting background model..."
	#	avg = gray.copy().astype("float")
	#	rawCapture.truncate(0)
	#	continue

	# accumulate the weighted average between the current frame and
	# previous frames, then compute the difference between the current
	# frame and running average
	#cv2.accumulateWeighted(gray, avg, 0.5)
	#frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

	# threshold the delta image, dilate the thresholded image to fill
	# in holes, then find contours on thresholded image
	#thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
#		cv2.THRESH_BINARY)[1]
#	thresh = cv2.dilate(thresh, None, iterations=2)
#	(cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
#		cv2.CHAIN_APPROX_SIMPLE)

	# loop over the contours
#	for c in cnts:
		# if the contour is too small, ignore it
#		if cv2.contourArea(c) < conf["min_area"]:
#			continue

		# compute the bounding box for the contour, draw it on the frame,
		# and update the text
#		(x, y, w, h) = cv2.boundingRect(c)
#		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
#		text = "Occupied"

	# draw the text and timestamp on the frame
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
#	cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
#		cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
#	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
#		0.35, (0, 0, 255), 1)

	# check to see if the room is occupied
	if text == "Occupied":
                print "Occupied"
		# check to see if enough time has passed between uploads
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
                        print "Within time"
			# check to see if dropbox sohuld be used
			if conf["use_dropbox"]:
				# write the image to temporary file
				t = TempImage()
				send_to_db_and_slack(t, frame, client, ts)

			# update the last uploaded timestamp and reset the motion
			# counter
			lastUploaded = timestamp

	# otherwise, the room is not occupied
	else:
		motionCounter = 0

	# check to see if the frames should be displayed to screen
	if conf["show_video"]:
		# display the security feed
#		cv2.imshow("Security Feed", frame)
#		key = cv2.waitKey(1) & 0xFF

		# if the `q` key is pressed, break from the lop
		if key == ord("q"):
			break

	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
