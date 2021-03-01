#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs.common import Logger, install
from libs.env import log_remote_level, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, ffmpeg_version

def main():
    """
        将libXau, libxcb, SDL2安装包放入编译好的ffmpeg下的deps目录
    """
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)

    log=Logger({"remote": log_remote_level})

    flag=0
    # 安装
    if action=="install":
        located=conf_dict["located"]
        pkg_file=conf_dict["pkg_file"]
        value, msg=install(pkg_file, ffmpeg_src, ffmpeg_dst, ffmpeg_pkg_dir, located)
        if not value:
            flag=1
            log.logger.error(msg)
        sys.exit(flag)

    elif action=="run" or action=="start" or action=="stop":
        sys.exit(flag)

if __name__ == "__main__":
    main()
