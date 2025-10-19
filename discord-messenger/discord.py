"""
discord.py

A Python script to send build notifications to a Discord server via webhook.

Features:
- Supports build actions: started, succeeded, failed.
- Accepts configuration via command-line arguments or a .ini config file.
- Automatically formats Discord embeds with project name, build target, and build link.

Usage:
- Command-line arguments:
    --project-name <name>
    --build-target <target>
    --build-action <started|succeeded|failed>
    --build-link <url>
    --discord-webhook-url <url>
    --config <path to .ini file>  # optional; overrides other args
"""

import argparse
import configparser
import http.client
import json
import os
import pathlib
from urllib.parse import urlparse

build_ops = ["succeeded", "failed", "started"]

def load_config_file(path: pathlib.Path) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"config file not found: {path}")

    config = configparser.ConfigParser()
    config.read(path)

    try:
        cfg = {
            "project_name": config.get("general", "project_name", fallback=None),
            "build_target": config.get("general", "build_target", fallback=None),
            "build_action": config.get("general", "build_action", fallback=None),
            "build_link": config.get("general", "build_link", fallback=None),
            "discord_webhook_url": config.get("general", "webhook_url", fallback=None),
        }
    except (configparser.NoOptionError, configparser.NoSectionError) as e:
        raise ValueError(f"config file '{path}' is not valid. {e}")
    
    # TODO: probably not needed because we do a check for None after this load (because args need the check too)
    for key, value in cfg.items():
        if value is None or not str(value).strip():
            raise ValueError(f"config field '{key}' is missing or empty")
        if cfg["build_action"] not in build_ops:
            raise ValueError(f"Invalid build_action: {cfg['build_action']}")
        
    return cfg

def build_standard_payload(args_project_name, args_build_target, args_build_action, args_build_link) -> str:
    colors = {
        "succeeded": "#00FF00", # Green
        "failed": "#FF0000", # Red
        "started": "#007BFF", # Blue
    }
    color_hex = colors.get(args_build_action)
    color = int(color_hex.lstrip("#"), 16)

    payload = {
        "embeds": [{
            "title": "Build " + args_build_action.title(),
            "color": color,
            "fields": [
                {
                    "name": "Project",
                    "value": args_project_name,
                    "inline": True
                },
                {
                    "name": "Build Target",
                    "value": args_build_target,
                    "inline": True
                },
                {
                    "name": "Build",
                    "value": f"[link]({args_build_link})",
                    "inline": False
                },
            ]
        }]
    }

    return json.dumps(payload)

def main() -> bool:
    # parse any arguments pased to the script
    parser = argparse.ArgumentParser("Script to send notifications")
    parser.add_argument("--project-name", type=str, required=False, help="The name of the Unity project")
    parser.add_argument("--build-target", type=str, required=False, help="The name of the build target or build profile")
    parser.add_argument("--build-action", type=str, required=False, choices=build_ops, help="The build action")
    parser.add_argument("--build-link", type=str, required=False, help="The link to the build operation")
    parser.add_argument("--discord-webhook-url", type=str, required=False, help="Webhook URL")
    parser.add_argument("--config", type=pathlib.Path, required=False, help="Optional link to a config file. This will ignore the other params")
    args = parser.parse_args()

    # handle the args
    args_project_name: str = args.project_name
    args_build_target: str = args.build_target
    args_build_action: str = args.build_action
    args_build_link: str = args.build_link
    args_webhook_url: str = args.discord_webhook_url
    print("args parsed")

    if args.config:
        try:
            cfg_values = load_config_file(args.config)
            args_project_name = cfg_values.get("project_name")
            args_build_target = cfg_values.get("build_target")
            args_build_action = cfg_values.get("build_action")
            args_build_link = cfg_values.get("build_link")
            args_webhook_url = cfg_values.get("discord_webhook_url")
            print("config loaded")
        except (FileNotFoundError, ValueError) as e:
            return False
    
    # ensure we have all args
    if not all([args_project_name, args_build_target, args_build_action, args_build_link, args_webhook_url]):
        print("missing args")
        return False

    # strip the important part of the webhook
    parsed = urlparse(args_webhook_url)
    webhook_api = parsed.path

    # build http message
    connection = http.client.HTTPSConnection("discord.com")
    headers = {"Content-Type": "application/json"}
    payload = build_standard_payload(args_project_name, args_build_target, args_build_action, args_build_link)
    print("payload built")

    # send http message
    print("trying to send msg")
    try:
        connection.request("POST", webhook_api, payload, headers)
        response = connection.getresponse()
    except http.client.HTTPException as e:
        print(f"HTTP error: {e}")
        return False
    finally:
        connection.close()

    return response.status == 204

if __name__ == "__main__":
    result: bool = main()
    print("message sent" if result else "message failed to send")