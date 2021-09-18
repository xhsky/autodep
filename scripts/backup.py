#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2021-09-18 09:57:23
# sky

import os, sys, json, logging, tarfile, time
from logging import handlers

def get_time_format():
    return time.strftime('%Y%m%d%H%M', time.localtime())

def backup_keep(dst_dir, keep_days, keyname):
    '''定时删除
    '''
    now_time=time.time()
    diff_time=keep_days*60*60*24
    if os.path.exists(dst_dir):
        logger.info("开始定时删除...")
        for filename in os.listdir(dst_dir):
            if filename.startswith(keyname) and filename.endswith("tar.gz"):
                filename_abs=f"{dst_dir}/{filename}"
                if os.path.isfile(filename_abs):
                    mtime=os.path.getmtime(filename_abs)
                    if now_time - mtime >= diff_time:
                        logger.info(f"删除'{filename_abs}'")
                        os.remove(filename_abs)

def remote_backup(remote_backup_dict):
    pass

def text_backup(src_dir, dst_dir, keyname):
    '''文本类备份
    return backup_file
    '''
    if os.path.exists(src_dir):
        time_format=get_time_format()
        dst_file=f"{dst_dir}/{keyname}-{time_format}.tar.gz"
        with tarfile.open(dst_file, "w:gz") as tar:
            tar.add(src_dir)
        return dst_file
    else:
        logger.error(f"备份目录({src_dir})不存在, 该备份忽略")
        return ""

def dm_backup():
    pass

def mysql_backup():
    pass

def logger_config(log_file, log_name):
    '''日志
    '''
    logger=logging.getLogger(log_name)
    logger.setLevel(level=logging.DEBUG)
    fmt='%(asctime)s - %(levelname)s: %(message)s'
    format_str=logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')                           # 设置日志格式

    fh=handlers.TimedRotatingFileHandler(filename=log_file, when="D", backupCount=7, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(format_str)                            # 设置文件里写入的格式
    logger.addHandler(fh)                             # 把对象加到logger里

    ch=logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fh.setFormatter(format_str)                            # 设置文件里写入的格式
    logger.addHandler(ch)                             # 把对象加到logger里

    return logger
    
if __name__ == "__main__":
    try:
        backup_home=os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        logger=logger_config(f"{backup_home}/logs/backup.log", "backup")
        conf_file=sys.argv[1]
        with open(conf_file, "r", encoding="utf8") as f:
            conf_dict=json.load(f)
    except Exception as e:
        logger.error(e)
        sys.exit(127)

    type_=conf_dict["type"]
    logger.info(f"开始备份({type_})...")

    keyname=conf_dict["keyword"]
    dst_dir=conf_dict["backup_dir"]
    os.makedirs(dst_dir, exist_ok=1)
    if type_=="text":
        src_dir=conf_dict["source_dir"]
        backup_file=text_backup(src_dir, dst_dir, keyname)
    elif type_=="dm" or type_=="dameng":
        pass
    elif type_=="mysql":
        pass

    if backup_file != "":
        logger.info(f"'{backup_file}'备份成功")

    keep_days=conf_dict.get("keep_days")
    if keep_days is not None:
        backup_keep(dst_dir, keep_days, keyname)

    if conf_dict.get("remote_backup") is not None:
        remote_backup(conf_dict["remote_backup"])


