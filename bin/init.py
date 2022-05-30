#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, stat, json, shutil
from libs.common import Logger
from libs.env import log_remote_level, normal_code, error_code, deps_dir

def main():
    log=Logger({"remote": log_remote_level}, logger_name="init")
    return_value=0

    libstdc_src_file=f"{deps_dir}/libstdc++.so.6.0.25"
    libstdc_dst_file=f"/usr/lib/aarch64-linux-gnu/{libstdc_src_file.split('/')[-1]}"
    if os.path.exists(libstdc_src_file):
        try:
            log.logger.debug(f"cp {libstdc_src_file} {libstdc_dst_file}")
            shutil.copyfile(libstdc_src_file, libstdc_dst_file)
            libstdc_link_dst_file="/usr/lib/aarch64-linux-gnu/libstdc++.so.6"
            if os.path.islink(libstdc_link_dst_file):
                os.remove(libstdc_link_dst_file)
            log.logger.debug(f"link {libstdc_dst_file} {libstdc_link_dst_file}")
            os.symlink(libstdc_dst_file, libstdc_link_dst_file)
        except Exception as e:
            log.logger.error(str(e))
            return_value=error_code

    rc_local="/etc/rc.local"
    if os.path.exists(rc_local):
        try:
            exit_flag=False
            with open(rc_local, "r", encoding="utf-8") as f:
                all_text=f.readlines()
                for index, line in enumerate(all_text):
                    if line.strip().startswith("exit"):
                        exit_flag=True
                        all_text.pop(index)
            if exit_flag:
                with open(rc_local, "w", encoding="utf-8") as f:
                    f.writelines(all_text)
        except Exception as e:
            log.logger.error(str(e))
            return_value=error_code
    else:
        with open(rc_local, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh -e\n")
        os.chmod(rc_local, 0o755)

    sys.exit(return_value)

if __name__ == "__main__":
    main()
