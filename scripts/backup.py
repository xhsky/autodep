#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2021-09-18 09:57:23
# sky

import os, sys, json, logging, tarfile, time
from logging import handlers
import paramiko
from subprocess import run

def get_time_format():
    return time.strftime('%Y%m%d%H%M', time.localtime())

def backup_keep(dst_dir, keep_days, keyname, type_, **kwargs):
    '''定时删除
    '''
    if type_=="local":
        if os.path.exists(dst_dir):
            for filename in os.listdir(dst_dir):
                if filename.startswith(keyname) and filename.endswith("tar.gz"):
                    filename_abs=f"{dst_dir}/{filename}"
                    if os.path.isfile(filename_abs):
                        mtime=os.path.getmtime(filename_abs)
                        if date_comp(keep_days, mtime):
                            logger.info(f"本地备份定时删除: '{filename_abs}'")
                            os.remove(filename_abs)
    elif type_=="remote":
        sftp=kwargs["sftp"]
        attr_list=sftp.listdir_attr(dst_dir)
        for f in attr_list:
            filename=f.filename
            if filename.startswith(keyname) and filename.endswith("tar.gz") and date_comp(keep_days, f.st_mtime):
                filename_abs=f"{dst_dir}/{filename}"
                logger.info(f"远程备份定时删除: '{filename_abs}'")
                sftp.remove(filename_abs)

def free_pass_set(remote_backup_dict):
    '''设置免密码登录, 返回ssh
    '''
    key_dir=f"{os.environ['HOME']}/.ssh"
    key_file=f"{key_dir}/id_rsa"
    key_pub_file=f"{key_dir}/id_rsa.pub"
    ip=remote_backup_dict["remote_backup_host"]
    user=remote_backup_dict["user"]
    password=remote_backup_dict["password"]
    port=remote_backup_dict["port"]

    ssh=paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

    if not os.path.exists(key_dir):
        logger.info(f"创建{key_dir}目录")
        os.mkdir(key_dir)
        os.chmod(key_dir, 0o700)

    if not os.path.exists(key_file) or not os.path.exists(key_pub_file):
        logger.info(f"生成公私钥文件")
        key=paramiko.rsakey.RSAKey.generate(2048)    # 生成私钥文件
        key.write_private_key_file(key_file)

        key_pub=key.get_base64() # 生成公钥文件
        key_pub_and_sign="%s%s" % (" ".join(["ssh-rsa", key_pub]), "\n")
        with open(key_pub_file, "w") as f:
            f.write(key_pub_and_sign)

    try:
        with open(key_pub_file, "r") as f:
            key_pub=f.read()
        ssh.connect(ip, port=port, username=user, key_filename=key_file, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
        logger.info(f"已实现免密码登录, 可直接远程备份")
    except Exception as e:
        try:
            ssh.connect(ip, port=port, username=user, password=password, timeout=60, banner_timeout=60, auth_timeout=60, allow_agent=False, look_for_keys=False)
        except Exception as e:
            logger.error(f"远程信息有误: {e}")
            sys.exit(127)

        logger.info("传输私钥...")
        if user=="root":
            ssh_dir="/root/.ssh"
        else:
            ssh_dir=f"/home/{user}/.ssh"

        sftp=ssh.open_sftp()
        try:
            sftp.stat(ssh_dir)
        except FileNotFoundError as e:
            sftp.mkdir(ssh_dir, 0o700)
        sftp_file=sftp.file(f"{ssh_dir}/authorized_keys", "a")
        sftp_file.write(key_pub)
        sftp_file.chmod(384)
        sftp_file.close()
        sftp.close()
        logger.info(f"{ip}免密码登录完成")
    return ssh

def date_comp(keep_days, mtime):
    '''判断mtime是否超过keey_days
    '''
    now_time=time.time()
    keep_days_time=keep_days*60*60*24
    return now_time - mtime >= keep_days_time

def remote_backup(remote_backup_dict, backup_file, keep_days):
    '''远程备份
    '''
    ssh=free_pass_set(remote_backup_dict)
    remote_backup_dir=remote_backup_dict["remote_backup_dir"]
    remote_file=f"{remote_backup_dir}/{backup_file.split('/')[-1]}"
    sftp=ssh.open_sftp()

    try:
        sftp.stat(remote_backup_dir)
    except FileNotFoundError as e:
        logger.info(f"创建远程备份目录'{remote_backup_dir}'")
        ssh.exec_command(f"mkdir -p {remote_backup_dir}")

    ip=remote_backup_dict["remote_backup_host"]
    logger.info(f"远程备份中: {backup_file} --> {ip}:{remote_file}")
    try:
        sftp.put(backup_file, remote_file, confirm=True)
        logger.info("远程备份完成")
        if keep_days is not None:
            backup_keep(remote_backup_dir, keep_days, keyname, "remote", sftp=sftp)
        sftp.close()
    except Exception as e:
        logger.error(f"远程备份失败: {e}")

def exec_command(command, timeout=45):
    try:
        result=run(command, capture_output=True, encoding="utf8", shell=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

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

def db_backup(dump_db_command, dump_db_file, dst_dir, dbname):
    '''
    '''
    logger.info(f"数据'{dbname}'备份中, 请稍后...")
    logger.debug(f"{dump_db_command=}")
    result, msg=exec_command(dump_db_command, timeout=3600)
    if result:
        logger.info(f"数据压缩中, 请稍后...")
        backup_file=text_backup(dump_db_file, dst_dir, dbname)
        if backup_file != "":
            if os.path.exists(dump_db_file):
                logger.info("清理数据包...")
                os.remove(dump_db_file)
        return backup_file
    else:
        logger.error(msg)
        return ""

def dm_backup(system_user, schema, dba_password, dst_dir):
    '''dm备份
    '''
    dba_user="sysdba"
    if system_user is None:
        system_user="root"
    db_abs_file=f"{dst_dir}/{schema}.dmp"
    dump_db_command=f"chown -R {system_user} {dst_dir} && su -l {system_user} -c 'dexp userid={dba_user}/{dba_password} file={db_abs_file} log=/tmp/{schema}.log owner={schema} dummy=Y LOG_WRITE=Y'"
    return db_backup(dump_db_command, db_abs_file, dst_dir, schema)

def mysql_backup(dbname, root_password, dst_dir):
    '''mysql数据库备份
    '''
    db_abs_file=f"{dst_dir}/{dbname}.sql"
    dump_db_command=f"mysqldump -uroot -p{root_password} --set-gtid-purged=OFF {db_name} > {db_abs_file}"
    return db_backup(dump_db_command, db_abs_file, dst_dir, dbname)

def logger_config(log_file, log_name):
    '''日志
    '''
    logger=logging.getLogger(log_name)
    logger.setLevel(level=logging.DEBUG)
    fmt='%(asctime)s - %(levelname)s: %(message)s'
    format_str=logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')                           # 设置日志格式

    fh=handlers.TimedRotatingFileHandler(filename=log_file, when="D", backupCount=7, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(format_str)                            # 设置文件里写入的格式
    logger.addHandler(fh)                             # 把对象加到logger里

    ch=logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fh.setFormatter(format_str)                            # 设置文件里写入的格式
    logger.addHandler(ch)                             # 把对象加到logger里

    return logger
    
if __name__ == "__main__":
    try:
        conf_file=sys.argv[1]
        backup_home=os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        with open(conf_file, "r", encoding="utf8") as f:
            conf_dict=json.load(f)
        keyname=conf_dict["keyword"]
        logger=logger_config(f"{backup_home}/logs/{keyname}.log", "backup")
    except Exception as e:
        print(e)
        sys.exit(127)

    type_=conf_dict["type"]
    logger.info(f"开始备份({type_})...")

    dst_dir=conf_dict["backup_dir"]
    os.makedirs(dst_dir, exist_ok=1)
    if type_=="text":
        src_dir=conf_dict["source_dir"]
        backup_file=text_backup(src_dir, dst_dir, keyname)
    elif type_=="dm" or type_=="dameng":
        system_user=conf_dict.get("system_user")
        dba_password=conf_dict["dba_password"]
        backup_file=dm_backup(system_user, keyname, dba_password, dst_dir)
    elif type_=="mysql":
        root_password=conf_dict["root_password"]
        backup_file=mysql_backup(keyname, root_password, dst_dir)

    if backup_file != "":
        logger.info(f"'{backup_file}'备份成功")

        keep_days=conf_dict.get("keep_days")
        if keep_days is not None:
            backup_keep(dst_dir, keep_days, keyname, "local")

        if conf_dict.get("remote_backup") is not None:
            remote_backup(conf_dict["remote_backup"], backup_file, keep_days)

