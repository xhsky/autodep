#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# 2021-01-13 14:51:02
# sky

import sys, json, os, time
import tarfile, shutil
from libs import common
from libs.env import log_remote_level, code_saved_remote_dir

def main():
    """
    用于本地代码更新
    """
    args_dict=json.loads(sys.argv[1])
    log=common.Logger({"remote": log_remote_level})

    type_=args_dict.get("type")
    tar_file=args_dict.get("tar_file")
    dest=args_dict.get("dest")

    if not os.path.exists(dest):
        try:
            log.logger.info(f"建立目录...")
            log.logger.debug(f"{dest=}")
            os.makedirs(dest, exist_ok=1)
        except Exception as e:
            log.logger.error(f"无法建立目录: {str(e)}")
            exit(1)

    try:
        with tarfile.open(tar_file, "r", encoding="utf8") as tar:
            if type_=="backend":
                log.logger.info("开始后端更新...")
                tar.extractall(dest)
            elif type_=="frontend":
                log.logger.info("开始前端更新...")
                for i in tar.getmembers():
                    if i.name != "update.json":
                        code_dir_name=i.name.split("/")[1]
                        break
                code_dir_abs=f"{dest}/{code_dir_name}"
                if os.path.exists(code_dir_abs):
                    time_format=time.strftime("%Y%m%d-%H:%M:%S", time.localtime())
                    save_dir=f"{code_saved_remote_dir}/{code_dir_name}_{time_format}"
                    log.logger.info(f"备份'{code_dir_abs}'至'{save_dir}'...")
                    shutil.move(code_dir_abs, save_dir)
                log.logger.debug(f"解压'{tar_file}'至'{dest}'")
                tar.extractall(dest)
            else:
                log.logger.error(f"{type_}不匹配")
                sys.exit(2)

            log.logger.info("清理更新包...")
            os.remove(tar_file)
    except Exception as e:
        log.logger.error(f"更新失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
