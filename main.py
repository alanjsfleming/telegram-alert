#import libraries
import machine
import urequests as requests
import utime
from secrets import secrets
from secrets import location_one
from secrets import location_two
import network
import rp2
import ubinascii


#define pins

# onboard led for status
led=machine.Pin("LED",machine.Pin.OUT)

# switch input to select recipient of text messages and wifi network to connect to
switchInput=machine.Pin(1,machine.Pin.IN,machine.Pin.PULL_DOWN)

# relay input to detect when test is started and finished
relayInput=machine.Pin(19,machine.Pin.IN,machine.Pin.PULL_DOWN)

#set the wifi country code
rp2.country('GB')

wlan=network.WLAN(network.STA_IF)
wlan.active(True)

#load data from different file for security
ssid=location_one['ssid']
pw=location_one['pw']
botToken=secrets['botToken']
chatId=secrets['telegramDmUid']

# Text for message templates
startupText='Pico started!'
dischargeStartedText='Battery discharge started'
dischargeFinishedText='Battery disconnected at 10.5V'


#state of discharge, initial, discharging, discharged
dischargeState='start'
totalTime=0


# If switch is in position 0, location one is the current user so use those details, if 1 then location two...
#Check switch for text recipient
def msgR():
    
    if switchInput.value()==0:
        chatId=location_one['telegramDmUid']
        print("one")
    elif switchInput.value()==1:
        chatId=location_two['telegramDmUid']
        print("two")
    return chatId

def selectedNetwork():
    if switchInput.value()==0:
        ssid=location_one['ssid']
        pw=location_one['pw']
        print("location one")
    elif switchInput.value()==1:
        ssid=secrets['ssid']
        pw=secrets['pw']
        print("mobile hotspot for testing")
    return(ssid,pw)
    

#telegram send message URL
# Send requests are posted to this endpoint
sendURL='https://api.telegram.org/bot' + botToken + '/sendMessage'


#function to handle relay change
# This is called every time the main loop cycles to check if the relay has changed state
def relaySwitch(dischargeState):
    # Global variables to be changed in this function and then used by the send completed text function
    global timeStarted, timeFinished
    print('called, ',dischargeState,', ',relayInput.value())


    # When the battery starts discharge cycle, goes from not being tested to being tested
    if dischargeState == 'start' and relayInput.value()==1:
        timeStarted=utime.time()
        send_message(dischargeStartedText)
        dischargeState='discharging'
        
        print(dischargeState,timeStarted)
        return dischargeState
    #When the battery stops discharge cycle (completed), goes from being tested to not being tested
    elif dischargeState == 'discharging' and relayInput.value()==0:
        timeFinished=utime.time()
        print("1")
        totalTime=dSTime(timeStarted,timeFinished)
        finalText=dischargeFinishedText+". "+totalTime
        send_message(finalText)
        
        dischargeState='discharged'
        
        print(dischargeState,totalTime)
        return dischargeState
    # If the discharge state has not changed then do nothing
    else:
        return dischargeState
        
#convert number of seconds into a string for total discharge time
def convertSeconds(seconds):
    seconds=seconds%(24*3600)
    hour=seconds//3600
    seconds%=3600
    minutes=seconds//60
    seconds%=60
    stringOut=f"Time taken {hour}:{minutes}:{seconds}"
    return stringOut
    
#function to determine total time taken for discharge
def dSTime(timeStarted,timeFinished):
    totalTime=convertSeconds(timeFinished-timeStarted)
    return totalTime

#Send a telegram message to a given user ID
def send_message (message):
    # Get the chat ID from the secrets depending on which switch position is selected
    chatId=msgR()
    # Send the request to the Telegram API
    response = requests.get(sendURL + "?chat_id=" + str(chatId) + "&text=" + message)
    # Close to avoid filling up the RAM.
    response.close()

#define blinking function for status
# Will blink slowly when waiting to connect, then blink fast 3 times and then stay on while connecting
def blink_onboard_led(num_blinks,speed):
    for i in range(num_blinks):
        led.on()
        utime.sleep(speed)
        led.off()
        utime.sleep(speed)

#function to disconnect and turn off
def turnProgramOff():
    led.off()
    wlan.disconnect()

#function to check if connected to wifi
def is_wifi_connected():
    wlan_status=wlan.status()
    if wlan_status !=3:
        return False
    else:
        return True

#Connect to wifi and send text to confirm connection.
def connect_wifi():
    while True:
        #If The wifi is connected, blink light to show status, print ip to console and sent startup text to user.
        if (is_wifi_connected()):
            blink_onboard_led(3,0.2)
            led.on()
            status=wlan.ifconfig()
            print('ip='+status[0])
            # Send text to users telegram to confirm tester is ready.
            send_message(startupText)
            break
        #If not connected to wifi, try to connect and flash lights.
        else:
            print('Wifi is disconnected. Trying to connect.')
            led.low()
            ssid,pw=selectedNetwork()
            wlan.connect(ssid,pw)
            blink_onboard_led(2,1)

#function for reconnecting if loses wifi midway through test
def reconnect_wifi():
    while True:
        if (is_wifi_connected()):
            led.on()
            status=wlan.ifconfig()
            print('reconnected: ip='+status[0])
            break
        else:
            print('Wifi is disconnected. Trying to reconnect.')
            led.low()
            wlan.connect(ssid,pw)
            blink_onboard_led(2,1)
            
#loop that runs once initial connection working  
def running_loop(dischargeState) :
    while True:
        if (is_wifi_connected()):
            #checks the state of discharge to see if any action required
            dischargeState=relaySwitch(dischargeState)
            utime.sleep(0.5)
        else:
            reconnect_wifi()


#This code runs initially
try:
    connect_wifi()
    print("Connected, text sent")
    running_loop(dischargeState)
    
#Handle errors
except OSError as e:
    if e=='-2':
        utime.sleep(1)
        connect_wifi() 
    print(e)
    led.off()
    wlan.disconnect()
    
