#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import tarfile, psutil
import os, time, socket
from subprocess import run
import textwrap
from logging import handlers
import logging


def exec_command(command, timeout=45):
    try:
        result=run(command, capture_output=True, encoding="utf8", shell=True, timeout=timeout)
        return True, result
    except Exception as e:
        result=str(e)
        return False, result

def port_exist(port_list, seconds=120):
    result=[]
    for port in port_list:
        N=0
        while True:
            time.sleep(1)
            N=N+1
            if N >= seconds:
                result.append(False)
                break
            for i in psutil.net_connections(kind="inet"):
                if port==i[3][1] and i[6] is not None:
                    result.append(True)
                    break
            else:
                continue
            break
                
    if False in result:
        return False
    else:
        return True

def port_connect(host, port):
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result=s.connect_ex((host, port))
    if result==0:
        return True
    else:
        return False

def install(soft_file, link_src, link_dst, pkg_dir, located):
    log=Logger({"remote": "debug"}, logger_name="remote install")
    os.makedirs(located, exist_ok=1)
    try:
        # 解压
        log.logger.debug(f"{soft_file=}解压")
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
        log.logger.debug(f"建立软连接: {src=} ==> {dst=}")
        os.symlink(src, dst)

        # 安装依赖
        if pkg_dir is not None:
            pkg_dir=f"{dst}/{pkg_dir}"
            pkg_list=os.listdir(pkg_dir)

            not_intall_pkg_list=[]  # 判断rpm是否已安装
            for i in pkg_list:
                command=f"rpm -q {i[:-4]} &> /dev/null"
                log.logger.debug(f"{command=}")
                if os.system(command) != 0:
                    not_intall_pkg_list.append(i)

            if len(not_intall_pkg_list) == 0:
                return True, None
            else:
                pkgs=" ".join(not_intall_pkg_list)
                command=f"cd {pkg_dir} && rpm -Uvh {pkgs} &> /dev/null"
                log.logger.info(f"{command=}")
                result=os.system(command)
                if result==0: 
                    return True, None
                else:
                    return False, result
        else:
            return True, None
    except Exception as e:
        return False, str(e)

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
        return True, None
    except Exception as e:
        return False, str(e)

class MessageFilter(logging.Filter):
    """
        含有DEBUG的信息不输出
    """
    def filter(self, record):
        if "DEBUG" in record.msg:
            return False
        return True

class MessageRewrite(logging.Filter):
    """
        将信息中的日志级别替换当前的日志级别, 并根据设定的日志级别决定是否输出
    """
    def filter(self, record):
        level_dict={
                "CRITICAL": 50, 
                "ERROR": 40, 
                "WARNING": 30, 
                "INFO": 20, 
                "DEBUG": 10, 
                "NOTSET": 0
                }
        for level in level_dict:
            if level == record.msg[:len(level)]:
                record.msg=record.msg[len(level)+2:]
                record.levelname=level
                record.levelno=level_dict[level]
                break
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
            logger_name="autodep"
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

        self.logger.addFilter(MessageRewrite())

        if log_to_console:
            self.ch=logging.StreamHandler()
            fmt="%(message)s"
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.ch.setLevel(self.level_relations[mode_level_dict["console"]])
            self.ch.setFormatter(format_str)
            #self.ch.addFilter(MessageFilter())
            self.logger.addHandler(self.ch)                             # 把对象加到logger里
        if log_to_file:
            self.fh=handlers.TimedRotatingFileHandler(filename=kwargs["log_file"], when="D", backupCount=7, encoding='utf-8')
            fmt='%(asctime)s - %(levelname)s: %(message)s'
            format_str=logging.Formatter(fmt)                           # 设置日志格式
            self.fh.setLevel(self.level_relations[mode_level_dict["file"]])
            self.fh.setFormatter(format_str)                            # 设置文件里写入的格式
            #self.fh.addFilter(MessageRewrite())
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
if __name__ == "__main__":
    main()
