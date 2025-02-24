import configparser
import os.path
import shutil
import threading
import phub.consts
import traceback
import itertools
import queue
from io import TextIOWrapper
from src.backend.shared_functions import *
from src.backend.log_config import setup_logging
from base_api.modules.progress_bars import *
from base_api.base import BaseCore
from rich import print as rprint
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn, TimeElapsedColumn, TimeRemainingColumn
from colorama import *
from base_api import base

base.disable_logging()
logger = setup_logging()
init(autoreset=True)

class CLI:
    def __init__(self):
        self.downloaded_segments = 0
        self.total_segments = 0 # Used for total progress tracking
        self.to_be_downloaded = 0
        self.finished_downloading = 0
        self.progress_queue = queue.Queue()
        self.skip_existing_files = None
        self.threading_mode = None
        self.result_limit = None
        self.directory_system = None
        self.output_path = None
        self.progress_thread = None
        self.quality = None
        self.semaphore = threading.Semaphore(9999999)  # No limit on semaphore
        self.retries = None
        self.conf = None
        self.timeout = None
        self.workers = 9999999  # No limit on workers
        self.delay = None
        self.language = None
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}", style="bold cyan"),  # Display task description here
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style="bold cyan"),
            BarColumn(bar_width=20, finished_style="bold green"),
            TextColumn("[bold green]{task.completed}[/] / {task.total}", style="bold yellow"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            SpinnerColumn(spinner_name="dots")
        )
        self.task_total_progres = self.progress.add_task("[progress.description]{task.description}", total=self.total_segments)

    def init(self):
        while True:
            setup_config_file()
            self.conf = ConfigParser()
            self.conf.read("config.ini")
            self.license()
            self.load_user_settings()
            self.menu()

    def license(self):
        if not self.conf["Setup"]["license_accepted"] == "true":
            license_text = input(f"""{Fore.WHITE}
GPL License Agreement for Porn Fetch
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License,[...]
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General [...]
You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.
NO LIABILITY FOR END USER USE
Under no circumstances and under no legal theory, whether in tort, contract, or otherwise, shall the copyright holder or contributors be liable to You for any direct, indirect, special, incidental, co[...]
This limitation of liability shall not apply to liability for death or personal injury resulting from such party’s negligence to the extent applicable law prohibits such limitation. Some jurisdictio[...]
This Agreement represents the complete agreement concerning the subject matter hereof.

Disclaimer:
Porn Fetch is NOT associated with any of the websites. Using this tool is against the ToS of every website. Usage of Porn Fetch is at your own risk. I (the developer) am not liable for any of your act[...]

Information:
Porn Fetch uses ffmpeg for video processing / converting. FFmpeg is free software licensed under the GPL license.
See more information on: https://FFmpeg.org


Do you accept the license?  [{Fore.LIGHTBLUE_EX}yes{Fore.RESET},{Fore.LIGHTRED_EX}no{Fore.RESET}]
---------------------------------->:""")

            if license_text == "yes":
                self.conf.set("Setup", "license_accepted", "true")
                with open("config.ini", "w") as config_file: #type: TextIOWrapper
                    self.conf.write(config_file)

            else:
                self.conf.set("Setup", "license_accepted", "false")
                with open("config.ini", "w") as config_file: #type: TextIOWrapper
                    self.conf.write(config_file)

                sys.exit()

    def menu(self):
        options = input(f"""
{return_color()}1) Download a Video
{return_color()}2) Get videos from a model
{return_color()}3) Get videos from a PornHub playlist
{return_color()}4) Search for videos
{return_color()}5) Search a file for URLs and Model URLs
{return_color()}6) Settings

{Fore.LIGHTWHITE_EX}98) Credits
{Fore.LIGHTRED_EX}99) Exit
{return_color()}------------------>:""")

        if options == "1":
            url = input(f"{return_color()}Please the enter video URL -->: {return_color()}")
            video = [check_video(url)]
            self.iterate_generator(auto=True, generator=video)

        elif options == "2":
            self.process_model(None, False)

        elif options == "3":
            self.process_playlist()

        elif options == "4":
            self.search_videos()

        elif options == "5":
            self.process_file()

        elif options == "6":
            self.save_user_settings()

        elif options == "98":
            self.credits()

        elif options == "99":
            sys.exit(0)

    def load_user_settings(self):
        self.delay = int(self.conf.get("Video", "delay"))
        self.workers = 9999999  # No limit on workers
        self.timeout = int(self.conf.get("Performance", "timeout"))
        self.retries = int(self.conf.get("Performance", "retries"))
        self.semaphore = threading.Semaphore(9999999)  # No limit on semaphore
        self.quality = self.conf.get("Video", "quality")
        self.output_path = self.conf.get("Video", "output_path")
        self.directory_system = True if self.conf.get("Video", "directory_system") == "1" else False
        self.skip_existing_files = True if self.conf.get("Video", "skip_existing_files") == "true" else False
        self.result_limit = None  # No limit on result
        self.threading_mode = self.conf.get("Performance", "threading_mode")

    def save_user_settings(self):
        while True:
            quality_color = {  # Highlight the current quality option in yellow
                "Best": Fore.LIGHTYELLOW_EX if self.quality == "best" else Fore.LIGHTWHITE_EX,
                "Half": Fore.LIGHTYELLOW_EX if self.quality == "half" else Fore.LIGHTWHITE_EX,
                "Worst": Fore.LIGHTYELLOW_EX if self.quality == "worst" else Fore.LIGHTWHITE_EX
            }
            threading_mode 
