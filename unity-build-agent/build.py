"""
build.py

This is the entry point for the app.
"""

import argparse
import configparser
import datetime
import pathlib
import platform
import os
import shutil
import subprocess
import time

APP_NAME = "unity-build-agent"

class BuildConfig:
    def __init__(self, name, editor_path, project_path, build_path, build_profile_path, full_rebuild, deploy_path):
        self.name = name
        self.editor_path = editor_path
        self.project_path = project_path
        self.build_path = build_path
        self.build_profile_path = build_profile_path
        self.full_rebuild = full_rebuild
        self.deploy_path = deploy_path
    
    def __repr__(self):
        return (f"BuildConfig(name={self.name!r},"
                f"editor_path={self.editor_path!r}, "
                f"project_path={self.project_path!r}, "
                f"build_path={self.build_path!r}, "
                f"build_profile_path={self.build_profile_path!r}, "
                f"full_rebuild={self.full_rebuild!r}, "
                f"deploy_path={self.deploy_path})")

def is_platform_supported() -> bool:
    if platform.system() == "Windows":
        return True
    elif platform.system() == "Linux":
        return True
    else:
        return False

def is_valid_path(path_string: str) -> bool:
    """
    Ensures the provided string is a valid path.

    Args:
        path_string (str): the path string to test.
    
    Returns:
        bool: True if a valid path string.
    """

    if not isinstance(path_string, str):
        return False
    
    try:
        pathlib.Path(path_string).resolve()
    except (OSError, ValueError):
        return False
    
    return True

#def build_project(editor_path: str, project_path: str, build_path: str, build_profile_path: str, full_rebuild: bool) -> bool:
def build_project(config: BuildConfig) -> bool:
    """
    Builds a project based on a given build profile and logs the results.
    \n See https://docs.unity3d.com/Manual/EditorCommandLineArguments.html
    \n See https://docs.unity3d.com/Manual/build-path-requirements.html

    Args:
        config (BuildConfig): The configuration for the build

    Returns:
        bool: True if the build completes successfully, False otherwise.
    """
    
    print(f"{config.name} build started")
    
    if not is_valid_path(config.editor_path):
        print("Invalid editor path provided.")
        return False
    
    if not is_valid_path(config.project_path):
        print("Invalid project path provided")
        return False
    
    if not is_valid_path(config.build_path):
        print("Invalid build path provided")
        return False
    
    if not is_valid_path(config.build_profile_path):
        print("Invalid build profile path provided")
        return False
    
    log_path = os.path.join(os.path.dirname(config.build_path), "build.log")

    # TODO: ./Unity is a linux only cmd, fix this for other platforms
    cmds = [
        "./Unity", "-batchmode", "-quit",
        "-projectPath", config.project_path,
        "-build", config.build_path,
        "-activeBuildProfile", config.build_profile_path,
        "-logFile", log_path
    ]

    # A full rebuild should delete the build dir so it cannot use any cached assets
    # It should also tell unity to rebuild the library
    if config.full_rebuild:
        build_dir = os.path.dirname(config.build_path)
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
        os.makedirs(build_dir)
        cmds.append("-rebuildLibrary")
        
    try:
        os.chdir(config.editor_path)
        
        start_time = time.time()
        
        # TODO: currently this process is uncancelable from python.
        # I would prefer to change to opening a handle, but then unity
        # never terminates with a handle kept. Figure out how to handle this.
        result: subprocess.CompletedProcess = subprocess.run(cmds)
        
        duration = time.time() - start_time
        duration_hms = f"{int(duration // 3600):02d}:{int((duration % 3600) // 60):02d}:{int(duration % 60):02d}"

        if result.returncode == 0:
            with open(log_path, 'r') as file:
                success = "Build Finished, Result: Success." in file.read()
                if success:
                    print(f"build completed successfully in {duration_hms}")
                    print(f"check log at {log_path}")
                else:
                    print(f"build failed in {duration_hms}")
                    print(f"check log at {log_path}")
                return success
        else:
            print(f"build failed in {duration_hms}")
            print(f"check log at {log_path}")
            return False
    except KeyboardInterrupt:
        # TODO: this is a problem because it doesnt fully close all unity processes.
        #       it puts the computer in a state where no more builds will work correctly.
        print("\n The unity build process cannot be cancelled. Terminate it manually")
    except OSError as e:
        print("Failed to change to editor directory:", e)
        return False
    except Exception as e:
        print(e)
        return False

def archive_project(config: BuildConfig, tagged_build: bool) -> bool:
    """
    Archives the project to the deploy_path

    Args:
        config (BuildConfig): The configuration for the build

    Returns:
        bool: True if the archive completes successfully, False otherwise.
    """

    print("archiving build")

    # ensure paths exists
    build_dir = os.path.dirname(config.build_path)
    if not os.path.exists(build_dir):
        print("build path does not exist, ensure project was built first.")
        return False

    if not os.path.exists(config.deploy_path):
        os.makedirs(config.deploy_path)

    # get bundle version
    bundle_version = ""
    project_settings_path = os.path.join(config.project_path, "ProjectSettings", "ProjectSettings.asset")
    try:
        with open(project_settings_path, 'r') as file:
            for line in file:
                clean_line = line.strip()
                if clean_line.startswith("bundleVersion:"):
                    bundle_version = clean_line.split(":")[1].strip().replace(".","_")
                    break
    except FileNotFoundError:
        print(f"project settings not found at {project_settings_path}")
        return False
    if bundle_version == "":
        print("bundle version not found")
        return False
    
    
    # build archive path name
    # TODO: figure out if I want to use tar or not. tar is uncompressed, but built into python.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tag_name = '-TAG' if tagged_build else ''
    archive_name = f"{config.name}-{bundle_version}-{timestamp}{tag_name}.tar"
    archive_path = os.path.join(config.deploy_path, archive_name)
    try:
        shutil.make_archive(archive_path.replace(".tar", ""), "tar", build_dir)
        print("archiving build succeeded")
        print(f"get build from {archive_path}")
        return True
    except Exception as e:
        print(e)
        print("archiving build failed")
        return False

def clean_deploy_dir(config: BuildConfig, retain_builds_count: int) -> bool:
    """
    Removes old auto builds from the deploy directory
    """

    print(f"cleaning old builds (keeping {retain_builds_count})")

    if not os.path.exists(config.deploy_path):
        print("deploy path does not exist, cannot clean")
        return False
    
    #builds = [f for f in os.listdir(deploy_path) if os.path.isfile(os.path.join(deploy_path, f)) and "-Tag" not in f]

    builds = [] # [filename, timestamp]

    # grab all builds that are not tag, then sort them by timestamp
    for filename in os.listdir(config.deploy_path):
        if '-TAG' not in filename:
            clean_filename = filename.replace("-TAG", "").replace(".tar","")
            timestamp = clean_filename.split("-")[-1] # grab last one
            builds.append([filename, timestamp])
    builds.sort(key=lambda build: build[1], reverse=True)

    # loop through builds to remove and remove it
    builds_to_remove = builds[retain_builds_count:]
    try:
        for build in builds_to_remove:
            filepath = os.path.join(config.deploy_path, build[0])
            os.remove(filepath)
            print(f"removed {build[0]}")
    except OSError as e:
        print(e)
        return False
    
    print("clean completed")
    return True


def build() -> int:
    # ensure platform is supported
    if not is_platform_supported():
        print(f"{platform.system()} not supported. Exiting...")
        return 1
    
    # parse any arguments pased to the script
    parser = argparse.ArgumentParser("Script to run unity builds")
    parser.add_argument("--config", type=pathlib.Path, help="Optional Path to config file")
    parser.add_argument("--tag", action="store_true", help="Optional flag to state if this is a tagged build or not. Tagged builds dont get cleaned. (default: false)")
    parser.add_argument("--retain-builds", type=int, help="Optional count to state how many builds should be kept. Rest are deleted. Does not affefct tagged builds. (default: 3)")
    args = parser.parse_args()

    # handle the args
    config_path = args.config or "config.ini"
    config_tagged_build = args.tag
    config_retain_builds_count = args.retain_builds or 3

    # ensure config file exists
    if not os.path.exists(config_path):
        print(f"{config_path} not found. Exiting...")
        return 1

    # parse config file and store them as configs[]
    configs = []
    config = configparser.ConfigParser()
    config.read(config_path)
    for section in config.sections():
        try:
            build_config = BuildConfig(
                name = section,
                editor_path=config[section]['editor_path'],
                project_path=config[section]['project_path'],
                build_path=config[section]['build_path'],
                build_profile_path=config[section]['build_profile_path'],
                full_rebuild=config.getboolean(section, 'full_rebuild'),
                deploy_path=config[section]['deploy_path']
            )
            configs.append(build_config)
        except KeyError:
            print(f"{section} has invalid configuration. Skipping...")
        except ValueError:
            print(f"{section} has invalid configuration. Skipping...")
    
    if len(configs) == 0:
        print(f"{config_path} had no configurations. Exiting...")
        return 1

    print(f"{len(configs)} configurations found. Starting builds...")
    for config in configs:
        print("")

        if build_project(config):
            archive_result = archive_project(config, config_tagged_build)
            clean_result = clean_deploy_dir(config, config_retain_builds_count)
            if archive_result and clean_result:
                print(f"\033[32m{config.name} build suceeded\033[0m")
            else:
                print(f"\033[31m{config.name} build failed\033[0m")
        else:
            print(f"\033[31m{config.name} build failed\033[0m")
    
    print("")
    print("builds complete")
    
if __name__ == "__main__":
    build()