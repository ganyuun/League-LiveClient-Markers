from League_LiveClient_Markers import LOGPATH, VODPATH, SETTINGSPATH
import send2trash, os, polars as pl, time, json

FAVSPATH = 'data/favoritedVODs.csv'

if (os.path.exists(SETTINGSPATH)):
    with open(SETTINGSPATH, mode = 'r', encoding = 'utf8') as f:
        settings = json.load(f)
        sizeLimit = int(settings.get('vodFolderSizeLimit'))
else: sizeLimit = 50 # vod folder size limit is 50gb unless otherwise specified

def delSpecificVid(fileName):
    if os.path.exists(os.path.join(VODPATH, fileName)): send2trash.send2trash(os.path.join(VODPATH, fileName))

def vodFolderSize():
    folderSize = 0

    for path, dirs, files in os.walk(VODPATH):
        for f in files:
            fp = os.path.join(path, f)
            folderSize += os.path.getsize(fp)
    
    folderSize = round(folderSize / (1024 ** 3), 3) # convert to gb

    if folderSize > sizeLimit: logger.info(f'VOD folder is {folderSize} GB, and above the limit of {sizeLimit} GB.')
    else: logger.info(f'VOD folder is {folderSize} GB, and not above the limit of {sizeLimit} GB.')

    return folderSize

def delOldVids():
    vods = []

    for entry in os.listdir(VODPATH):
        path = os.path.join(VODPATH, entry)
        if os.path.isfile(path): vods.append(entry)
    
    vods.sort() # make sure vods are sorted oldest to newest

    # create new list, filtering out favorites
    nonFavs = []

    for file in vods:
        if file in favVods: logger.info(f"Removing {file} from candidates for deletion, since it's a favorite.")
        else: nonFavs.append(file)
    
    for file in nonFavs:
        size = vodFolderSize()

        if size <= sizeLimit:
            break
        
        send2trash.send2trash(os.path.join(VODPATH, file))
        logger.info(f'Deleting {file}. Folder is now {size}.')
        vods.remove(file)

if __name__ == '__main__':
    import logging
    
    logger = logging.getLogger(__name__)
    fh = logging.FileHandler(LOGPATH, encoding='utf-8')
    ch = logging.StreamHandler()

    logger.setLevel(logging.DEBUG)
    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)
    
    if os.path.exists(FAVSPATH):
        favVods = pl.read_csv(FAVSPATH)['Name'].to_list()
        logger.info('Favorite VODs: %s', favVods)

        size = vodFolderSize()
        if size > sizeLimit: delOldVids()
        else: logger.info('Exiting...\n-------------------\n')
        time.sleep(7)
    else:
        logger.warning("favoritedVODs.csv doesn't exist. Exiting...\n-------------------\n")
        time.sleep(7)