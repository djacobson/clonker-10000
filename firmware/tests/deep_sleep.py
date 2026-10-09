# CLONKER 10000 — Deep Sleep Test
# Feather ESP32 V2 / CircuitPython
#
# Run manually from the REPL:
# import tests.deep_sleep
#
# The board will deep-sleep for 5 seconds,
# then reboot into code.py.

import time
import alarm
import wifi

print("CLONKER DEEP SLEEP TEST")
print("-----------------------")
print("Wi-Fi connected:", wifi.radio.connected)

print("Entering deep sleep in 3 seconds...")
time.sleep(3)

wake_alarm = alarm.time.TimeAlarm(
    monotonic_time=time.monotonic() + 5
)

print("Goodnight, Clonker!")
print("Wake timer: 5 seconds")

# Deep sleep exits Python entirely.
# Execution will NOT continue past this call.
alarm.exit_and_deep_sleep_until_alarms(wake_alarm)
