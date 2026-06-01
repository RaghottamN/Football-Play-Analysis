from SoccerNet.Downloader import SoccerNetDownloader
dl = SoccerNetDownloader(LocalDirectory="/Users/raghottamgirishnadgoudar/RVCE/4th_sem/AEC/uploads")
try:
    print(dl.getListFiles(task="tracking", split=["train"]))
except Exception as e:
    print(e)
