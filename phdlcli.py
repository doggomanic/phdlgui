import configparser
import os.path
import shutil
import threading
import argparse
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
from rich.markdown import Markdown
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn, TimeElapsedColumn, TimeRemainingColumn
from colorama import *
from hue_shift import return_color
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
        self.semaphore = None
        self.retries = None
        self.conf = None
        self.timeout = None
        self.workers = None
        self.delay = None
        self.language = None
        self.ffmpeg_features = True
        self.ffmpeg_path = None
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
        # Please just don't ask, thank you :)

    def init(self):
        while True:
            setup_config_file()
            self.conf = ConfigParser()
            self.conf.read("config.ini")
            self.license()
            self.ffmpeg_recommendation()
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

    def ffmpeg_recommendation(self):
        if os.path.exists("/data/data/com.termux/files/home"):
            ffmpeg = input(f"""
Hey,

It seems like you are using Termux... I highly recommend you to use FFmpeg as your threading mode, because downloading
HLS segments is very slow on Android devices, because the processor and the system in general can't handle so many
threads at the same time.

You can install FFmpeg with: 'apt-get install ffmpeg'

If you accept, Porn Fetch will close and automatically set ffmpeg as your downloader.

Do you want to use FFmpeg? [yes,no]        
    """)

            if ffmpeg.lower() == "yes":
                self.conf.set("Performance", "threading_mode", "FFMPEG")
                with open("config.ini", "w") as config_file: #type: TextIOWrapper
                    self.conf.write(config_file)
                    print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Done!")

    def load_user_settings(self):
        self.delay = int(self.conf.get("Video", "delay"))
        self.workers = int(self.conf.get("Performance", "workers"))
        self.timeout = int(self.conf.get("Performance", "timeout"))
        self.retries = int(self.conf.get("Performance", "retries"))
        self.semaphore = threading.Semaphore(int(self.conf.get("Performance", "semaphore")))
        self.quality = self.conf.get("Video", "quality")
        self.output_path = self.conf.get("Video", "output_path")
        self.directory_system = True if self.conf.get("Video", "directory_system") == "1" else False
        self.skip_existing_files = True if self.conf.get("Video", "skip_existing_files") == "true" else False
        self.result_limit = int(self.conf.get("Video", "search_limit"))
        self.threading_mode = self.conf.get("Performance", "threading_mode")

        try:
            if shutil.which("ffmpeg"):
                self.ffmpeg_path = shutil.which("ffmpeg")

            else:
                if os.path.isfile("ffmpeg"):
                    self.ffmpeg_path = "ffmpeg"

                elif os.path.isfile("ffmpeg.exe"):
                    self.ffmpeg_path = "ffmpeg.exe"

                else:
                    logger.warning("FFMPEG wasn't found... Have you extracted it from the .zip file?")
                    logger.warning("FFMPEG Features won't be available!")
                    self.ffmpeg_features = False
        finally:
            if not self.ffmpeg_path == "":
                phub.consts.FFMPEG_EXECUTABLE = self.ffmpeg_path
                bs_consts.FFMPEG_PATH = self.ffmpeg_path
                self.ffmpeg_features = True

    def save_user_settings(self):
        while True:
            quality_color = {  # Highlight the current quality option in yellow
                "Best": Fore.LIGHTYELLOW_EX if self.quality == "best" else Fore.LIGHTWHITE_EX,
                "Half": Fore.LIGHTYELLOW_EX if self.quality == "half" else Fore.LIGHTWHITE_EX,
                "Worst": Fore.LIGHTYELLOW_EX if self.quality == "worst" else Fore.LIGHTWHITE_EX
            }
            threading_mode_color = {  # Highlight the current threading mode in yellow
                "threaded": Fore.LIGHTYELLOW_EX if self.threading_mode == "threaded" else Fore.LIGHTWHITE_EX,
                "ffmpeg": Fore.LIGHTYELLOW_EX if self.threading_mode == "ffmpeg" else Fore.LIGHTWHITE_EX,
                "default": Fore.LIGHTYELLOW_EX if self.threading_mode == "default" else Fore.LIGHTWHITE_EX
            }

            settings_options = input(f"""
{Fore.LIGHTYELLOW_EX}YELLOW {Fore.LIGHTWHITE_EX} = Currently selected / Current value
            
{Fore.LIGHTWHITE_EX}--------- {Fore.LIGHTGREEN_EX}Quality {Fore.LIGHTWHITE_EX}----------
1) {quality_color["Best"]}Best{Fore.LIGHTWHITE_EX}
2) {quality_color["Half"]}Half{Fore.LIGHTWHITE_EX}
3) {quality_color["Worst"]}Worst{Fore.LIGHTWHITE_EX}
{Fore.LIGHTWHITE_EX}-------- {Fore.LIGHTCYAN_EX}Performance {Fore.LIGHTWHITE_EX}--------
4) Change Semaphore {Fore.LIGHTYELLOW_EX}(current: {self.semaphore._value}){Fore.LIGHTWHITE_EX}
5) Change Delay {Fore.LIGHTYELLOW_EX}(current: {self.delay}){Fore.LIGHTWHITE_EX}
6) Change Workers {Fore.LIGHTYELLOW_EX}(current: {self.workers}){Fore.LIGHTWHITE_EX}
7) Change Retries {Fore.LIGHTYELLOW_EX}(current: {self.retries}){Fore.LIGHTWHITE_EX}
8) Change Timeout {Fore.LIGHTYELLOW_EX}(current: {self.timeout}){Fore.LIGHTWHITE_EX}
-------- {Fore.LIGHTYELLOW_EX}Directory System {Fore.LIGHTWHITE_EX}---
9) Enable / Disable directory system {Fore.LIGHTYELLOW_EX}(current: {"Enabled" if self.directory_system else "Disabled"}){Fore.LIGHTWHITE_EX}
{Fore.LIGHTWHITE_EX}-------- {Fore.LIGHTGREEN_EX}Result Limit {Fore.LIGHTWHITE_EX}-------
10) Change result limit {Fore.LIGHTYELLOW_EX}(current: {self.result_limit}){Fore.LIGHTWHITE_EX}
{Fore.LIGHTWHITE_EX}-------- {Fore.LIGHTBLUE_EX}Output Path {Fore.LIGHTWHITE_EX}--------
11) Change output path {Fore.LIGHTYELLOW_EX}(current: {self.output_path}){Fore.LIGHTWHITE_EX}
{Fore.LIGHTWHITE_EX}---------{Fore.LIGHTMAGENTA_EX}Threading Mode {Fore.LIGHTWHITE_EX}---------
12) {threading_mode_color["threaded"]}Change to threaded (Not recommended on Android!){Fore.LIGHTWHITE_EX}
13) {threading_mode_color["ffmpeg"]}Change to FFmpeg (Recommended on Android){Fore.LIGHTWHITE_EX}
14) {threading_mode_color["default"]}Change to default (really slow){Fore.LIGHTWHITE_EX}
{Fore.LIGHTRED_EX}99) Exit
{Fore.WHITE}------------->:""")

            try:
                if settings_options == "1":
                    self.conf.set("Video", "quality", "best")

                elif settings_options == "2":
                    self.conf.set("Video", "quality", "half")

                elif settings_options == "3":
                    self.conf.set("Video", "quality", "worst")

                elif settings_options == "4":
                    limit = input(f"Enter a new Semaphore limit -->:")
                    self.conf.set("Performance", "semaphore", limit)

                elif settings_options == "5":
                    limit = input(f"Enter a new delay (seconds) -->:")
                    self.conf.set("Video", "delay", limit)

                elif settings_options == "6":
                    limit = input(f"Enter a new value for max workers -->:")
                    self.conf.set("Performance", "workers", limit)

                elif settings_options == "7":
                    limit = input(f"Enter a new value for max retries -->:")
                    self.conf.set("Performance", "retries", limit)

                elif settings_options == "8":
                    limit = input(f"Enter a new value for the max timeout -->:")
                    self.conf.set("Performance", "timeout", limit)

                elif settings_options == "9":
                    if self.directory_system:
                        self.conf.set("Video", "directory_system", "0")

                    else:
                        self.conf.set("Video", "directory_system", "1")

                elif settings_options == "10":
                    limit = input(f"Enter a new result limit -->:")
                    self.conf.set("Video", "search_limit", limit)

                elif settings_options == "11":
                    path = input(f"Enter a new output path -->:")
                    if not os.path.exists(path):
                        raise "The specified output path doesn't exist!"

                    self.conf.set("Video", "output_path", path)

                elif settings_options == "12":
                    self.conf.set("Performance", "threading_mode", "threaded")

                elif settings_options == "13":
                    self.conf.set("Performance", "threading_mode", "FFMPEG")

                elif settings_options == "14":
                    self.conf.set("Performance", "threading_mode", "default")

                elif settings_options == "99":
                    self.menu()

            finally:
                with open("config.ini", "w") as config_file: #type: TextIOWrapper
                    self.conf.write(config_file)

    def process_video(self, url=None, batch=False):
        self.semaphore.acquire()

        if url is None:
            url = input(f"{return_color()}Please enter the Video URL -->:")

        video = check_video(url=url)
        data = load_video_attributes(video)
        author = data.get("author")
        title = data.get("title")

        output_path = self.output_path

        if self.directory_system:
            path_author = os.path.join(output_path, author)
            if not os.path.exists(path_author):
                os.makedirs(path_author, exist_ok=True) # doesn't make sense ik

            output_path = os.path.join(str(path_author), title + ".mp4")

        else:
            output_path = os.path.join(output_path, title + ".mp4")

        if os.path.exists(output_path):
            logger.debug(f"{return_color()}File: {output_path} already exists, skipping...")
            print(f"{return_color()}File: {output_path} already exists, skipping...")
            self.semaphore.release()
            return

        # Create the progress task
        task = self.progress.add_task(description=f"[bold cyan]Downloading: {video.title}[/bold cyan]", total=100)

        # Start the download thread
        self.progress.start()
        self.download_thread = threading.Thread(target=self.download, args=(video, output_path, task))
        self.download_thread.start()

        self.progress_thread = threading.Thread(target=self._update_progress)
        self.progress_thread.start()


        if batch:
            self.download_thread.join()

    def process_video_with_error_handling(self, video, batch, ignore_errors):
        try:
            print(f"Processing video: {video.title}")
            self.process_video(video, batch=batch)
        except Exception as e:
            if ignore_errors:
                print(f"{Fore.LIGHTRED_EX}[~]{Fore.RED}Ignoring Error: {e}")
            else:
                raise f"{Fore.LIGHTRED_EX}[~]{Fore.RED}Error: {e}, please report the full traceback --: {traceback.print_exc()}"

    def iterate_generator(self, generator, auto=False, ignore_errors=False, batch=False):
        videos = []

        for idx, video in enumerate(generator):
            print(f"{idx}) - {video.title}")
            videos.append(video)

        print(f"Videos loaded: {len(videos)}")

        if not auto:
            vids = input(f"""
    {return_color()}Please enter the numbers of videos you want to download with a comma separated.
    for example: 1,5,94,3{Fore.WHITE}

    Enter 'all' to download all videos

    {return_color()}------------------------>:{Fore.WHITE}""")
        else:
            vids = "all"

        if vids == "all" or auto:
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Calculating the total progress... This may take some time!")

            self.total_segments = sum(
                [len(list(video.get_segments(quality=self.quality))) for video in videos if
                hasattr(video, 'get_segments')])
            logger.debug(f"Got segments: {self.total_segments}")

            self.to_be_downloaded = len(videos)
            self.download_in_batches(videos, batch, ignore_errors)
        else:
            selected_videos = vids.split(",")
            videos_ = []
            for number in selected_videos:
                videos_.append(videos[int(number)])

            self.total_segments = sum(
                [len(list(video.get_segments(quality=self.quality))) for video in videos_ if
                hasattr(video, 'get_segments')])

            self.to_be_downloaded = len(selected_videos)
            self.download_in_batches(videos_, batch, ignore_errors)

    def download_in_batches(self, videos, batch, ignore_errors):
        for i in range(0, len(videos), 10):
            batch_videos = videos[i:i + 10]
            threads = []
            for video in batch_videos:
                thread = threading.Thread(target=self.process_video_with_error_handling, args=(video, batch, ignore_errors))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()

    def process_model(self, url=None, do_return=False, auto=False, ignore_errors=False, batch=False):
        if url is None:
            model = input(f"{return_color()}Enter the model URL -->:")

        else:
            model = url

        if eporner_pattern.search(model):
            model = ep_Client().get_pornstar(model, enable_html_scraping=True).videos(pages=10)

        elif xnxx_pattern.match(model):
            model = xn_Client().get_user(model).videos

        elif pornhub_pattern.match(model):
            model = itertools.chain(Client().get_user(model).videos, Client().get_user(model).uploads)

        elif hqporner_pattern.match(model):
            model = hq_Client().get_videos_by_actress(model)
