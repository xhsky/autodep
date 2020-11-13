#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import tarfile, psutil
import os, time
import textwrap
import logging
from logging import handlers

def port_exist(port, seconds=300):
    N=0
    while True:
        time.sleep(1)
        N=N+1
        if N >= seconds:
            return 0
        for i in psutil.net_connections():
            if port==i[3][1] and i[6] is not None:
                return 1
        print(".")

def install(soft_file, link_src, link_dst, pkg_dir, located):
    os.makedirs(located, exist_ok=1)

    try:
        # 解压
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        # 建立软连接
        for i in os.listdir(located):
            if i.startswith(link_src):
                src=f"{located}/{i}"
                break
        dst=f"{located}/{link_dst}"
        if os.path.exists(dst) and os.path.islink(dst):
            os.remove(dst)
        os.symlink(src, dst)

        # 安装依赖
        """
        ffmpeg 768
        glusterfs 5120
        """
        if pkg_dir is not None:
            pkg_dir=f"{dst}/{pkg_dir}"
            pkg_list=os.listdir(pkg_dir)

            not_intall_pkg_list=[]  # 判断rpm是否已安装
            for i in pkg_list:
                command=f"rpm -q {i[:-4]} &> /dev/null"
                if os.system(command) !=0 :
                    not_intall_pkg_list.append(i)

            if len(not_intall_pkg_list) == 0:
                return 1, "Installed"
            else:
                pkgs=" ".join(not_intall_pkg_list)
                command=f"cd {pkg_dir} && rpm -Uvh {pkgs} &> /dev/null"
                result=os.system(command)
                if result==0: 
                    return 1, "ok"
                else:
                    return 0, result
        else:
            return 1, "ok"
    except Exception as e:
        return 0, e

def config(config_dict):
    """
    config_dict={
        config1:{
            config_file: /path/dir/file, 
            config_context: str, 
            mode: a
        }, 
        config2:{
            config_file: /path/dir/file, 
            config_context: str, 
            mode: r+
        } 
    }
    """

    try:
        for config in config_dict:
            mode=config_dict[config]["mode"]
            context=textwrap.dedent(config_dict[config]["config_context"])
            filename=config_dict[config]["config_file"]
            if mode=="w" or mode=="a":
                with open(filename, mode, encoding="utf-8") as f:
                    f.write(context)
            elif mode=="r+":
                with open(filename, mode, encoding="utf-8") as f:
                    all_text=f.readlines()
                    if context not in all_text:
                        f.write(context)
        return 1, "ok"
    except Exception as e:
        return 0, e
class Logger(object):
    level_relations = {         #日志级别关系映射
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }

    def __init__(self, filename, level, mode="file", g_file="wfile"):
        log_to_file=0
        log_to_console=0
        log_to_remote=0
        log_to_graphical=0
        if filename is None:
            filename=mode
        self.logger=logging.getLogger(filename)
        self.logger.setLevel(self.level_relations["info"])

        #if mode=="all":
        #    log_to_file=1
        #    log_to_console=1
        if mode=="file":
            self.logger.setLevel(self.level_relations[level])
            log_to_file=1
        elif mode=="console":
            log_to_console=1
            log_to_file=1
        elif mode=="remote":
            log_to_remote=1
        elif mode=="graphical":
            log_to_graphical=1

        if log_to_file:
            fmt='%(asctime)s - %(levelname)s: %(message)s'
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.fh=handlers.TimedRotatingFileHandler(filename=filename, when="D", backupCount=7, encoding='utf-8')
            self.fh.setFormatter(format_str)                                 # 设置文件里写入的格式
            self.logger.addHandler(self.fh)                                  # 把对象加到logger里
        if log_to_console:
            self.sh=logging.StreamHandler()
            fmt="%(message)s"
            #fmt="%(levelname)s: %(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.sh.setFormatter(format_str)
            self.logger.addHandler(self.sh)                                  # 把对象加到logger里
        if log_to_remote:
            self.sh=logging.StreamHandler()
            #fmt="%(message)s"
            fmt="%(levelname)s: %(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.sh.setFormatter(format_str)
            self.logger.addHandler(self.sh)                                  # 把对象加到logger里
        if log_to_graphical:
            wfile=g_file
            self.sh=logging.StreamHandler(wfile)
            fmt="%(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.sh.setFormatter(format_str)
            self.logger.addHandler(self.sh)                                  # 把对象加到logger里

def main():
    import os
    import dialog
    import time
    d=dialog.Dialog()
    read_fd, write_fd = os.pipe()
    #g_log=Logger(write_fd, "info", "graphical")
    child_pid = os.fork()
    if child_pid == 0:
        os.close(read_fd)
        with os.fdopen(write_fd,  mode="w",  buffering=1) as wfile:
            g_log=Logger(wfile, "info", "graphical")
            for i in range(3):
                g_log.logger.info("aaaaa")
                time.sleep(2)

        os._exit(0)
    os.close(write_fd)
    d.programbox(fd=read_fd, title="hhhhhhhhh")

    exit_info = os.waitpid(child_pid, 0)[1]
    if os.WIFEXITED(exit_info):
        exit_code = os.WEXITSTATUS(exit_info)
    elif os.WIFSIGNALED(exit_info):
        pass

if __name__ == "__main__":
    main()
