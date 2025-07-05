#!/usr/bin/env python
import os, sys, time
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'packet_mon.settings')
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django; django.setup()

def main(poll_interval=10):
    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running poll_gns3_metrics…")
        try:
            call_command('poll_metrics')
        except Exception as e:
            print("Error in poll_gns3_metrics:", e)
        time.sleep(poll_interval)

if __name__ == '__main__':
    main(poll_interval=30)
