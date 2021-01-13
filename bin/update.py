#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# 2021-01-13 14:51:02
# sky

import sys, json, os, time
import tarfile, shutil
from libs import common
from libs.env import log_remote_level, code_saved_remote_dir, update_version_file

def main():
    args_dict=json.loads(sys.argv[1])
    log=common.Logger({"remote": log_remote_level})

    tar_file=args_dict.get("tar_file")
    dest_dir=args_dict.get("dest_dir")
    version=args_dict.get("version")

    if not os.path.exists(dest_dir):
        try:
            log.logger.info(f"建立目录...")
            os.makedirs(dest_dir, exist_ok=1)
        except Exception as e:
            log.logger.error(f"无法建立目录: {str(e)}")
            exit(1)

    try:
        with tarfile.open(tar_file, "r") as tar:
            file_list=tar.getmembers()
            code_dir_name=file_list[0].name
            code_dir=f"{dest_dir}/{code_dir_name}"

            if len(file_list) == 2 and file_list[1].name.endswith("jar"):            # 后端更新
                log.logger.info("后端更新...")
                tar.extractall(dest_dir)
            else:                               # 前端更新
                log.logger.info("前端更新...")
                if os.path.exists(code_dir):
                    time_format=time.strftime("%Y%m%d-%H:%M:%S", time.localtime())
                    save_dir=f"{code_saved_remote_dir}/{code_dir_name}_{time_format}"

                    log.logger.info(f"移动'{code_dir}'至'{save_dir}'...")
                    shutil.move(code_dir, save_dir)
                tar.extractall(dest_dir)

            log.logger.info(f"标记版本号({version})...")
            with open(f"{code_dir}/{update_version_file}", "w", encoding="utf8") as f:
                f.write(str(version))

            log.logger.info("清理更新包...")
            os.remove(tar_file)

    except Exception as e:
        log.logger.error("更新失败: {str(e)}")
        sys.exit(1)
    
if __name__ == "__main__":
    main()
