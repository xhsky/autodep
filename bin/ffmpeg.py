#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common

def main():
    """
        将libXau, libxcb, SDL2安装包放入编译好的ffmpeg下的deps目录
    """
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    soft_name="ffmpeg"

    log=common.Logger(None, "info", "remote")

    # 安装
    if action=="install":
        located=conf_dict.get("located")
        value, msg=common.install(soft_file, "ffmpeg", "ffmpeg", "deps", located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")

    elif action=="start":
            log.logger.info(f"{soft_name}无须启动")

if __name__ == "__main__":
    main()
