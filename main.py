#this file will handle loading the settings and importing plugins, mods and connectors and then starting the server

import signal
import sys

def signal_handler(sig, frame):
    print('Shutting down...')
    context_manager._shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Your main program loop
try:
    # ... your main program ...
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
finally:
    context_manager._shutdown()