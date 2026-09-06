from League_LiveClient_Markers import LOGPATH, VODPATH, SETTINGSPATH, DBPATH, migrateToSQLite
import send2trash, os, polars as pl, time, json, sqlite3

FAVSPATH = 'data/favoritedVODs.csv'

if (os.path.exists(SETTINGSPATH)):
    with open(SETTINGSPATH, mode = 'r', encoding = 'utf8') as f:
        settings = json.load(f)
        sizeLimit = int(settings.get('vodFolderSizeLimit'))
else: sizeLimit = 50 # vod folder size limit is 50gb unless otherwise specified

def delSpecificVid(file, path = VODPATH, permanent = False):
    con = sqlite3.connect(DBPATH)
    cur = con.cursor()

    if permanent:
        os.remove(os.path.join(path, file))
        if path == VODPATH: cur.execute("DELETE FROM videos WHERE Filename = ?", (file,))
    else:
        cur.execute("UPDATE videos SET Status = 'Trash' WHERE Filename = ?", (file,))

    con.commit()

def vodFolderSize():
    folderSize = 0

    for path, dirs, files in os.walk(VODPATH):
        for f in files:
            fp = os.path.join(path, f)
            folderSize += os.path.getsize(fp)
    
    folderSize = round(folderSize / (1024 ** 3), 3) # byte > GB conversion

    return folderSize

def delOldVids():
    con = sqlite3.connect(DBPATH)
    cur = con.cursor()

    vods = []

    for entry in os.listdir(VODPATH):
        path = os.path.join(VODPATH, entry)
        if os.path.isfile(path): vods.append(entry)
    
    vods.sort() # make sure vods are sorted oldest to newest

    # create list of vods in folder, minus favorites
    if os.path.exists(FAVSPATH):
        nonFavs = [vod for vod in vods if vod not in pl.read_csv(FAVSPATH)['Name'].to_list()]
    else:
        nonFavs = [vod for vod in vods if vod not in pl.read_database("SELECT * FROM favorites", connection = con)['Filename'].to_list()]

    logger.info(f"Removed all favorites from list of candidates for deletion.")

    if os.path.exists(FAVSPATH):
        for file in nonFavs:
            size = vodFolderSize()

            if size <= sizeLimit: break
            
            send2trash.send2trash(os.path.join(VODPATH, file))
            logger.info(f'Deleting {file}. Folder is now {size}.')
            vods.remove(file)
    else:
        expiring = pl.read_database("SELECT Filename FROM videos WHERE Status = 'Trash' AND Expires >= date('now')", connection = con)['Filename'].to_list()
        logger.info('VODs in the trash that have yet to expire: %s', expiring)

        expiredNow = pl.read_database("SELECT Filename FROM videos WHERE Status = 'Trash' AND Expires <= date('now')", connection = con)['Filename'].to_list()
        logger.info("Expired VODs: %s", expiredNow)
                
        if len(expiredNow) > 0:
            for vod in expiredNow:
                try:
                    os.remove(os.path.join(VODPATH, vod))
                    cur.execute("DELETE FROM videos WHERE Filename = ?", (vod,))
                    nonFavs.remove(vod)
                except Exception as e:
                    logger.warning("Failed to remove %s:", e)
            logger.info("Permanently deleted VODs that have been in the trash for 7 days.")

        expiringVodSize = 0

        for vod in expiring:
            expiringVodSize += os.path.getsize(os.path.join(VODPATH, vod)) / (1024 ** 3)

        anticipatedFolderSize = vodFolderSize() - round(expiringVodSize, 3)

        if anticipatedFolderSize > sizeLimit:
            toRemove = []

            for file in nonFavs:
                anticipatedFolderSize -= os.path.getsize(os.path.join(VODPATH, file)) / (1024 ** 3)
                
                cur.execute("UPDATE events SET Status = 'Trash' WHERE Filename = ?", (file,))
                toRemove.append(file)
                logger.info("Added %s as a candidate for deletion to be permanently deleted in 7 days. The folder will be %.3f GB after its deletion.", file, anticipatedFolderSize)

                if round(anticipatedFolderSize, 3) <= sizeLimit: break

            logger.info("VOD folder will be %s GB after the following VODs are deleted in 7 days: %s", anticipatedFolderSize, toRemove)
        else: logger.info("VOD folder will be %s GB (under the %s GB limit) after VODs that are currently in the trash are deleted.", anticipatedFolderSize, sizeLimit)

        con.commit()

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

    if os.path.exists('./data/events.csv') or os.path.exists('./data/favoritedVODs.csv'):
        migrateToSQLite()

    folderSize = vodFolderSize()

    if folderSize > sizeLimit: 
        logger.info("VOD folder is %s GB, and above the limit of %s GB.", folderSize, sizeLimit)
        delOldVids()
    else: logger.info('VOD folder size does not exceed the size limit. Exiting...\n-------------------\n')

    time.sleep(7)