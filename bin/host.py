#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import psutil
import platform
import os
from textwrap import dedent
from libs.common import Logger

def format_size(byte):
    byte=float(byte)
    kb=byte/1024

    if kb >= 1024:
        mb=kb/1024
        if mb>=1024:
            gb=mb/1024 
            return f"{gb:.2f}G"
        else:
            return f"{mb:.2f}M"
    else:
        return f"{kb:.2f}k"

def host_info(log):
    os_name, hostname, kernel_version=list(platform.uname())[0:3]
    redhat_file="/etc/redhat-release"
    if os.path.exists(redhat_file):
        with open(redhat_file, "r") as f:
            os_name=f.read().strip()

    # disk
    disk_list=[]
    all_disk=psutil.disk_partitions()
    for i in all_disk:
        #disk_name=i[0]
        mounted=i[1]
        size=psutil.disk_usage(mounted)
        total=size[0]
        used_percent=size[3]
        disk_list.append((mounted, total, used_percent))

    # cpu
    cpu_count=psutil.cpu_count()
    cpu_used_percent=psutil.cpu_percent(interval=2)

    # mem
    mem=psutil.virtual_memory()
    mem_total, mem_used_percent=mem[0], mem[2]

    return hostname, os_name, kernel_version, \
            cpu_count, cpu_used_percent, \
            mem_total, mem_used_percent, \
            disk_list

def main():
    log=Logger(None, "info", "remote")
    info=host_info(log)
    msg=f"""\
            主机名: \t{info[0]}
            发行版: \t{info[1]}
            内核版本: \t{info[2]}
            CPU核心数: \t{info[3]}({info[4]}%)
            内存大小: \t{format_size(info[5])}({info[6]}%)
    """
    dedent_msg=dedent(msg)
    for i in info[7]:
        disk_msg=f"磁盘({i[0]}): \t{format_size(i[1])}({i[2]}%)\n"
        dedent_msg=f"{dedent_msg}{disk_msg}"

    log.logger.info(f"{dedent_msg}")

if __name__ == "__main__":
    main()
