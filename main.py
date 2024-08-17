#import libraries
import machine
import urequests as requests
import utime
from secrets import secrets,location_one,location_two
import network
import rp2
import ubinascii

# Constants
STARTUP_TEXT = 'Pico started!'
DISCHARGE_STARTED_TEXT = 'Battery discharge started'
DISCHARGE_FINISHED_TEXT = 'Battery disconnected at 10.5V'

# Global variables
discharge_state = 'start'
time_started = 0
time_finished = 0

# Define pins
led = machine.Pin("LED",machine.Pin.OUT) # Status LED
switch_input = machine.Pin(1,machine.Pin.IN,machine.Pin.PULL_DOWN)
relay_input = machine.Pin(19,machine.Pin.IN,machine.Pin.PULL_DOWN)

# Set up WiFi
rp2.country('GB')
wlan=network.WLAN(network.STA_IF)
wlan.active(True)

# Load data from different file for security
ssid=location_one['ssid']
pw=location_one['pw']
botToken=secrets['botToken']
chatId=secrets['telegramDmUid']


#state of discharge, initial, discharging, discharged
dischargeState='start'
totalTime=0


def get_network_details():
    if switch_input.value() == 0:
        return location_one['ssid'], location_one['pw'], location_one['telegramDmUid']
    else:
        return location_two['ssid'], location_two['pw'], location_two['telegramDmUid']
    
def is_wifi_connected():
    return wlan.status() == 3

def blink_onboard_led(num_blinks,speed):
    for _ in range(num_blinks):
        led.on()
        utime.sleep(speed)
        led.off()
        utime.sleep(speed)


def connect_wifi():
    ssid,pw,_ = get_network_details()
    while not is_wifi_connected():
        led.off()
        wlan.connect(ssid,pw)
        blink_onboard_led(2,1)
    blink_onboard_led(3,0.2)
    led.on()
    status=wlan.ifconfig()
    print('ip='+status[0])
    send_message(STARTUP_TEXT)

def send_message(message):
    _,_,chat_id = get_network_details()
    response = requests.get(f'https://api.telegram.org/bot{secrets["botToken"]}/sendMessage?chat_id={chat_id}&text={message}')
    response.close()

def format_discharge_time(start_time,end_time):
    total_seconds = end_time - start_time
    hours,remainder = divmod(total_seconds,3600)
    minutes,seconds = divmod(remainder,60)
    return f'Time taken: {hours}:{minutes}:{seconds}'

def check_relay_switch():
    global discharge_state,time_started,time_finished
    if discharge_state == 'start' and relay_input.value() == 1:
        time_started = utime.time()
        send_message(DISCHARGE_STARTED_TEXT)
        discharge_state = 'discharging'
    elif discharge_state == 'discharging' and relay_input.value() == 0:
        time_finished = utime.time()
        total_time = format_discharge_time(time_started,time_finished)
        final_text = f'{DISCHARGE_FINISHED_TEXT}. {total_time}'
        send_message(final_text)
        discharge_state = 'discharged'

def main():
    try:
        connect_wifi()
        while True:
            if is_wifi_connected():
                check_relay_switch()
                utime.sleep(0.5)
            else:  
                connect_wifi()
    except Exception as e:
        send_message(f'Error: {e}')
        utime.sleep(5)
        machine.reset()

if __name__ == '__main__':
    main()
