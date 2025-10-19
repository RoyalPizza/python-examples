# Discord Webhook Notification Script

## Overview
A simple Python script to send build status notifications (succeeded, failed, started) to a Discord webhook. It supports configuration via command-line arguments or a config file. This project is intended to stay small and simple for ease of use, not flexibility.

## Features
- Sends Discord notifications with customizable embed colors based on build status.
- Accepts project details via command-line arguments or a `.ini` config file.
- Validates inputs and handles errors gracefully.
- Uses HTTP client to post messages to Discord's webhook API.

## Requirements
- Python 3.6+
- Modules: (standard library only)