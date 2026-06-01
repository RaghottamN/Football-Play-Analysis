from SoccerNet.Downloader import SoccerNetDownloader
import os

dl = SoccerNetDownloader(LocalDirectory="/Users/raghottamgirishnadgoudar/RVCE/4th_sem/AEC/uploads")
dl.password = "Please Provide Password" # It might prompt otherwise
try:
    # Try downloading tracking train split
    dl.downloadDataTask(task="tracking", split=["train"])
except Exception as e:
    print(f"Error: {e}")
