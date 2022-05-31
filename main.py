import sys, datetime, subprocess, time, logging, argparse
from pathlib import Path

logging.getLogger().setLevel(logging.INFO)

args = None

# root = Path(f'/home/brandon/cam')
root = Path(f'/mnt/e/cam')

encoding_lib = 'libx264'

raw = 'rtsp'
staging = 'h264'
archive = 'archive'

raw_dir = root/raw
staging_dir = root/staging
archive_dir = root/archive


def make_dirs():
    for p in [raw_dir, staging_dir, archive_dir]:
        p.mkdir(parents=True, exist_ok=True)

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
    
def launch_converter_process(path, mode, encoding_preset):

    singlepass_x264 = rf'ffmpeg -i input -vcodec {encoding_lib} -preset {encoding_preset} -timecode 00:00:00.00 output.mp4'

    twopass_x264 =\
    rf"ffmpeg -y -i input -c:v {encoding_lib} -preset {args.preset} -b:v {args.bitrate} -timecode 00:00:00.00 " \
    rf"-pass 1 -an -f null /dev/null " \
    rf"&& ffmpeg -i input -c:v {encoding_lib} -preset {args.preset} -b:v {args.bitrate} -timecode 00:00:00.00 " \
    rf"-pass 2 -c:a aac -b:a 128k output.mp4"

    if args.mode == 'lowres':
        cmdline = singlepass_x264[:]
    elif args.mode == 'highres':
        cmdline = twopass_x264[:]
    new_path = staging_dir/path.name.replace(raw, staging)
    cmdline = cmdline.replace('input', str(path)).replace('output.mp4', str(new_path))
    logging.info(f'running command line: {cmdline}')
    res = subprocess.run(cmdline, shell=True)
    return res.returncode

def archive_files(files):
    for p in files:
        ts = get_datetime(p.name)
        d = root/archive_dir/ts.strftime('%Y%m%d')
        d.mkdir(parents=True, exist_ok=True)
        p.rename(d/p.name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="should be one of [lowres|highres] depending on if we DVR 2.7K or 640p video from cam.")
    parser.add_argument("-preset", help="the 'preset' option passed through to ffmpeg, e.g [fast|slow|medium|...]")
    parser.add_argument('-bitrate', help="if mode=highres, then this specifies the bitrate, passed through to ffmpeg via -b:v [bitrate], e.g. '2600k' for 200MB 10min files")
    global args
    args = parser.parse_args()
    if args.mode not in {'lowres','highres'}:
        logging.error('mode argument must be one of [lowres|highres]')
        sys.exit()
    if not args.preset:
        args.preset = 'medium'
        logging.info('no preset provided, defaulting to "medium"')
    if args.mode == 'highres' and not args.bitrate:
        args.bitrate = '2600k'
        logging.info('no bitrate specified for highres 2pass, using default="2600k" which gives 200MB 10min files')

    make_dirs()

    while(True):
        # convert any files in root/rtsp folder
        ready2convert = get_files_older_than(root/raw_dir, 605, 'rtsp*.mp4')
        for f in ready2convert:
            ret = launch_converter_process(f, args.mode, args.preset)
            if ret == 0:
                f.unlink()
        
        # archive files into daily folders
        archive_files(get_files_older_than(staging_dir, 1*24*60*60, f'{staging}*.mp4'))
        
        logging.info('sleeping 10 seconds...')
        time.sleep(10)

if __name__ == "__main__":
    main()
