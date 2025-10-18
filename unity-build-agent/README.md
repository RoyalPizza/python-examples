# Unity Build Agent
A simple python script for automating unity builds.
This project is targeting simplicity and small scale.

- python utility to trigger builds based on config file
- runs each build and exports it to a deploy location
- handles cleanup to delete auto builds
- supports build tagging

<img width="800" height="311" alt="unity agent" src="https://github.com/user-attachments/assets/53529bc7-bc70-418f-b080-8ffcc75702ab" />

It is intended to stay a utility script, but long term can be part of an ecosystem where it can be triggered via http.
Future versions will become more and more automated.

## Example Config

[My Game Release]
editor_path=/home/user/Unity/Hub/Editor/6000.0.42f1/Editor
project_path=/home/user/project
build_path=/home/user/project/Build/game.x86_64
build_profile_path=Assets/Settings/Build Profiles/Linux Release.asset
full_rebuild=False

deploy_path=/home/user/Unity Builds/project/Release
