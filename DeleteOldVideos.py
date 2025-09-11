from League_LiveClient_Markers import VODPATH
import send2trash, os, polars as pl, time

FAVSPATH = '../favoritedVODs.csv'
sizeLimit = 50 # 50 gb limit

def delSpecificVid(fileName):
    if os.path.exists(os.path.join(VODPATH, fileName)):
        send2trash.send2trash(os.path.join(VODPATH, fileName))

def vodFolderSize():
    folderSize = 0

    for path, dirs, files in os.walk(VODPATH):
        for f in files:
            fp = os.path.join(path, f)
            folderSize += os.path.getsize(fp)
    
    folderSize = round(folderSize / (1024 ** 3), 3) # convert to gb
    print(f'VOD folder is {folderSize} GB')

    if folderSize > sizeLimit: print(f'VOD folder size is above the limit of {sizeLimit} GB')
    else: print(f'VOD folder size is not above the limit of {sizeLimit} GB')

    return folderSize

def delOldVids():
    vods = []

    for entry in os.listdir(VODPATH):
        path = os.path.join(VODPATH, entry)
        if os.path.isfile(path):
            vods.append(entry)
    
    vods.sort() # make sure vods are sorted oldest to newest

    # remove favVods from list (will be used for possible deletion)
    for file in vods:
        if file in favVods:
            vods.remove(file)
    
    for file in vods:
        size = vodFolderSize()

        if size <= sizeLimit:
            break
        
        send2trash.send2trash(os.path.join(VODPATH, file))
        print(f'Deleting {file}. Folder is now {size}')
        vods.remove(file)

if __name__ == '__main__':
    if os.path.exists(FAVSPATH):
        favVods = pl.read_csv(FAVSPATH)
        favVods = favVods['Name'].to_list()
        print('Favorite VODs:', favVods)

        size = vodFolderSize()
        if size > sizeLimit: delOldVids()
        else: print('Exiting...')
        time.sleep(7)
    else:
        print("favoritedVODs.csv doesn't exist. Exiting...")
        time.sleep(7)