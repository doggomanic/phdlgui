import gc
gc.disable()
import sys
import time
import httpx
import random
import shutil
import tarfile
import os.path
import zipfile
import argparse
import markdown
import traceback
from threading import Event
from io import TextIOWrapper
from itertools import islice, chain
from hqporner_api.api import Sort as hq_Sort

from src.backend.class_help import *
from src.backend.shared_functions import *
from src.backend.log_config import setup_logging

logger = setup_logging()
logger.setLevel(logging.DEBUG)

__license__ = "GPL 3"
__version__ = "3.5"
__build__ = "desktop"  # android or desktop
__author__ = "Johannes Habel"
__next_release__ = "3.6"
total_segments = 0
downloaded_segments = 0
stop_flag = Event()

url_linux = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz"
url_windows = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z"
url_macOS = "https://evermeet.cx/ffmpeg/ffmpeg-7.1.zip"
session_urls = []  # This list saves all URls used in the current session. Used for the URL export function
total_downloaded_videos = 0 # All videos that actually successfully downloaded
total_downloaded_videos_attempt = 0 # All videos the user tries to download

class VideoData:
    data_objects = {}
    consistent_data = {}

    def clean_dict(self, video_titles):
        if not isinstance(video_titles, list):
            video_titles = [video_titles]

        for video_title in video_titles:
            del self.data_objects[video_title]

class Signals:
    def __init__(self):
        self.total_progress = None
        self.progress_add_to_tree_widget = None
        self.progress_pornhub = None
        self.progress_hqporner = None
        self.progress_eporner = None
        self.progress_xnxx = None
        self.progress_xvideos = None
        self.progress_missav = None
        self.progress_xhamster = None
        self.ffmpeg_converting_progress = None
        self.start_undefined_range = None
        self.stop_undefined_range = None
        self.install_finished = None
        self.internet_check = None
        self.result = None
        self.error_signal = None
        self.clear_tree_widget_signal = None
        self.text_data_to_tree_widget = None
        self.download_completed = None
        self.progress_send_video = None
        self.url_iterators = None
        self.ffmpeg_download_finished = None

class FFMPEGDownload:
    def __init__(self, url, extract_path, mode):
        self.url = url
        self.extract_path = extract_path
        self.mode = mode
        self.signals = Signals()

    @staticmethod
    def delete_dir():
        deleted_any = False
        cwd = os.getcwd()

        for entry in os.listdir(cwd):
            if "ffmpeg" in entry.lower():
                full_path = os.path.join(cwd, entry)
                if os.path.isdir(full_path):
                    try:
                        shutil.rmtree(full_path)
                        logger.info(f"Deleted folder: {full_path}")
                        deleted_any = True
                    except Exception as e:
                        logger.error(f"Error deleting folder {full_path}: {e}")
        return deleted_any

    def run(self):
        logger.debug(f"Downloading: {self.url}")
        logger.debug("FFMPEG: [1/4] Starting the download")
        with httpx.stream("GET", self.url) as r:
            r.raise_for_status()
            if self.url == url_windows or self.url == url_macOS:
                total_length = int(r.headers.get('content-length'))
            else:
                total_length = 41964060

            self.signals.total_progress.emit(0, total_length)
            dl = 0
            filename = self.url.split('/')[-1]
            with open(filename, 'wb') as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        self.signals.total_progress.emit(dl, total_length)

        logger.debug("FFMPEG: [2/4] Starting file extraction")
        if self.mode == "linux" and filename.endswith(".tar.xz"):
            with tarfile.open(filename, "r:xz") as tar:
                total_members = len(tar.getmembers())

                for idx, member in enumerate(tar.getmembers()):
                    if 'ffmpeg' in member.name and (member.name.endswith('ffmpeg')):
                        tar.extract(member, self.extract_path, filter="data")
                        extracted_path = os.path.join(self.extract_path, member.path)
                        shutil.move(extracted_path, "./")

                    self.signals.total_progress.emit(idx, total_members)

                os.chmod("ffmpeg", 0o755)

        elif self.mode == "windows" and filename.endswith(".zip"):
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                total = len(zip_ref.namelist())

                for idx, member in enumerate(zip_ref.namelist()):
                    if 'ffmpeg.exe' in member:
                        zip_ref.extract(member, self.extract_path)
                        extracted_path = os.path.join(self.extract_path, member)
                        shutil.move(extracted_path, ".")

                    self.signals.total_progress.emit(idx, total)

        elif self.mode == "macOS" and filename.endswith(".zip"):
            with zipfile.ZipFile(filename, mode='r') as archive:
                archive.extractall(path=self.extract_path)

            os.chmod("ffmpeg", 0o755)

        logger.debug("FFMPEG: [3/4] Finished Extraction")
        self.signals.total_progress.emit(total_length, total_length)
        os.remove(filename)

        if self.delete_dir():
            logger.debug("FFMPEG: [4/4] Cleaned Up")
        else:
            logger.error("The Regex for finding the FFmpeg version failed. Please report this on GitHub!, Thanks.")

        self.signals.ffmpeg_download_finished.emit()

class AddUrls:
    def __init__(self, file, delay):
        self.signals = Signals()
        self.file = file
        self.delay = delay

    def run(self):
        iterator = []
        model_iterators = []
        search_iterators = []

        with open(self.file, "r") as url_file:
            content = url_file.read().splitlines()

        for idx, line in enumerate(content):
            if len(line) == 0:
                continue

            total = len(content)

            if line.startswith("model#"):
                line = line.split("#")[1]
                model_iterators.append(line)
                search_iterators.append(line)

            elif line.startswith("search#"):
                query = line.split("#")[1]
                site = line.split("#")[2]
                search_iterators.append({"website": site, "query": query})

            else:
                video = check_video(line)

                if video is not False:
                    iterator.append(video)

            self.signals.total_progress.emit(idx, total)

        self.signals.url_iterators.emit(iterator, model_iterators, search_iterators)

def main():
    send_error_log("Running in main function")
    setup_config_file()
    send_error_log("Finished setting up configuration file")

    conf = ConfigParser()
    conf.read("config.ini")

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", help="Shows the version information", action="store_true")
    args = parser.parse_args()

    if args.version:
        print(__version__)
    else:
        send_error_log("Did License stuff yk")

if __name__ == "__main__":
    main()
