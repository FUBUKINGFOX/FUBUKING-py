import time
from bin import ctc, event_logger
#===============
def load_playchannel() :
    file_ = "play_channel.cfg"
    playchannel = []
    with open(file = f"./config/{file_}", mode = "r", encoding = "utf-8") as id_ :
        for i in id_.readlines() :
            playchannel.append(int(i.strip()))

    event_logger.info_logger(f"{file_} loaded...")
    print("channel_id:")
    for w in playchannel :
        ctc.printDarkGreen(str(w)+"\n")
    time.sleep(0.5)
    return playchannel

    #===============

def load_songs_filter(bool: bool) :
    file_ = "songs_filter.cfg"
    filter = []
    if bool :
        with open(file = f"./config/{file_}", mode = "r", encoding = "utf-8") as id_ :
            for i in id_.readlines() :
                filter.append(i.strip())
        event_logger.info_logger(f"{file_} loaded...")

    return filter
