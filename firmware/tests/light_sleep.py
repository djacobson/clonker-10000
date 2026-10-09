import time
import alarm
import wifi

print("CLONKER LIGHT SLEEP TEST")

for test in range(3):
    print("Test", test + 1)
    print("Wi-Fi before:", wifi.radio.connected)

    start = time.monotonic()

    wake_alarm = alarm.time.TimeAlarm(
        monotonic_time=time.monotonic() + 5
    )

    alarm.light_sleep_until_alarms(wake_alarm)

    elapsed = time.monotonic() - start

    print("Awake after:", elapsed, "seconds")
    print("Wi-Fi after:", wifi.radio.connected)
    print("----------------")

print("Test complete.")

while True:
    time.sleep(1)
