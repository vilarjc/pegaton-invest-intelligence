#!/usr/bin/env python3
import datetime

def main():
    now = datetime.datetime.now()
    # Format: YYYY-MM-DD HH:MM:SS
    print(now.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()