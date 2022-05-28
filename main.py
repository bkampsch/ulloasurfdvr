import os, datetime, subprocess, time, logging
from pathlib import Path

logging.getLogger().setLevel(logging.INFO)

root = Path(f'/home/brandon/cam')
raw = 'rtsp'
staging = 'h265'
archive = 'archive'

raw_dir = root/raw
staging_dir = root/staging
archive_dir = root/archive

def get_datetime(s):
    return datetime.datetime(int(s[5:9]), int(s[10:12]), int(s[13:15]), int(s[16:18]), int(s[19:21]))

def get_files_older_than(path, seconds, globstr):
    files = [x for x in path.glob(globstr)]
    ret = []
    for f in files:
        ts = get_datetime(f.name)
        diff = datetime.datetime.now() - ts
        if diff.total_seconds() > seconds:
            ret.append(f)
    return sorted(ret)
    
def launch_converter_process(path):
    new_path = staging_dir/path.name.replace(raw, staging)
    cmdline = f'ffmpeg -i {str(path)} -vcodec libx265 -crf 28 -preset superfast -timecode 00:00:00.00 {str(new_path)}'
    res = subprocess.run(cmdline.split())
    return res.returncode

def archive_files(files):
    for p in files:
        ts = get_datetime(p.name)
        d = root/archive_dir/ts.strftime('%Y%m%d')
        d.mkdir(parents=True, exist_ok=True)
        p.rename(d/p.name)

def main():

    while(True):
        # convert any files in root/rtsp folder
        ready2convert = get_files_older_than(root/raw_dir, 605, 'rtsp*.mp4')
        for f in ready2convert:
            ret = launch_converter_process(f)
            if ret == 0:
                f.unlink()
        
        # archive files into daily folders
        archive_files(get_files_older_than(staging_dir, 1*24*60*60, f'{staging}*.mp4'))
        
        logging.info('sleeping 10 seconds...')
        time.sleep(10)

if __name__ == "__main__":
    main()
