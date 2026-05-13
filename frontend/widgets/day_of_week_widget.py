#!/usr/bin/env python3
import datetime

def main():
    now = datetime.datetime.now()
    # Format: Full weekday name (e.g., Monday)
    print(now.strftime("%A"))

if __name__ == "__main__":
    main()