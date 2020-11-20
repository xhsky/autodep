#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import tarfile, psutil
import os, time, socket
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

def port_connect(host, port):
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result=s.connect_ex((host, port))
    if result==0:
        return True
    else:
        return False

def install(soft_file, link_src, link_dst, pkg_dir, located):
    log=Logger(None, "info", "remote")
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
        if pkg_dir is not None:
            pkg_dir=f"{dst}/{pkg_dir}"
            pkg_list=os.listdir(pkg_dir)

            not_intall_pkg_list=[]  # 判断rpm是否已安装
            for i in pkg_list:
                command=f"rpm -q {i[:-4]} &> /dev/null"
                log.logger.info(f"{command=}")
                if os.system(command) !=0 :
                    not_intall_pkg_list.append(i)

            if len(not_intall_pkg_list) == 0:
                return 1, "Installed"
            else:
                pkgs=" ".join(not_intall_pkg_list)
                #command=f"cd {pkg_dir} && rpm -Uvh {pkgs} &> /dev/null"
                command=f"cd {pkg_dir} && rpm -Uvh {pkgs}"
                log.logger.info(f"{command=}")
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

class MessageFilter(logging.Filter):
    def filter(self, record):
        if "DEBUG" in record.msg:
            return False
        return True

class MessageRewrite(logging.Filter):
    def filter(self, record):
        for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]:
            if level == record.msg[:len(level)]:
                record.msg=record.msg[len(level)+2:]
                record.levelname=level
        return True

class Logger(object):
    level_relations = {         #日志级别关系映射
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }

    #def __init__(self, filename, level, mode="file", g_file="wfile"):
    def __init__(self, mode_level_dict, **kwargs):
        log_to_file=0
        log_to_console=0
        log_to_remote=0
        log_to_graphical=0
        log_to_platform=0

        if kwargs.get("logger_name") is None:
            logger_name="main"
        else:
            logger_name=kwargs["logger_name"]
        
        
        self.logger=logging.getLogger(logger_name)
        self.logger.setLevel(self.level_relations["debug"])

        for mode in mode_level_dict:
            if mode=="file":
                log_to_file=1
            elif mode=="console":
                log_to_console=1
            elif mode=="remote":
                log_to_remote=1
            elif mode=="graphical":
                log_to_graphical=1
            elif mode=="platform":
                log_to_platform=1

        if log_to_console:
            self.ch=logging.StreamHandler()
            fmt="%(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.ch.setLevel(self.level_relations[mode_level_dict["console"]])
            self.ch.setFormatter(format_str)
            self.ch.addFilter(MessageFilter())
            self.logger.addHandler(self.ch)                             # 把对象加到logger里
        if log_to_file:
            self.fh=handlers.TimedRotatingFileHandler(filename=kwargs["log_file"], when="D", backupCount=7, encoding='utf-8')
            fmt='%(asctime)s - %(levelname)s: %(message)s'
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.fh.setLevel(self.level_relations[mode_level_dict["file"]])
            self.fh.setFormatter(format_str)                            # 设置文件里写入的格式
            self.fh.addFilter(MessageRewrite())
            self.logger.addHandler(self.fh)                             # 把对象加到logger里
        if log_to_remote:
            self.rh=logging.StreamHandler()
            fmt="%(levelname)s: %(message)s"
            self.rh.setLevel(self.level_relations[mode_level_dict["remote"]])
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.rh.setFormatter(format_str)
            self.logger.addHandler(self.rh)                             # 把对象加到logger里
        if log_to_graphical:
            wfile=g_file
            self.gh=logging.StreamHandler(wfile)
            fmt="%(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.gh.setLevel(self.level_relations[mode_level_dict["graphical"]])
            self.gh.setFormatter(format_str)
            self.logger.addHandler(self.gh)                             # 把对象加到logger里
        if log_to_platform:
            pass
            """
            fmt="%(levelname)s: %(message)s"
            self.ph=handlers.HTTPHandler(host, url, method="POST")
            self.ph.setLevel(self.level_relations[mode_level_dict["platform"]])
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.logger.addHandler(self.ph)
            """


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
def main1():
    log=Logger("platform", "info")
    log.logger.info("aaa")

if __name__ == "__main__":
    main1()
