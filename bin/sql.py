#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, tarfile
from libs import common
from libs.env import log_remote_level, backup_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=normal_code
    db_tar_file=conf_dict["pkg_file"]
    value, msg=common.install(db_tar_file, None, None, None, install_dir)
    if not value:
        log.logger.error(msg)
        return error_code
    return return_value

def run():
    """运行
    """
    db_file=os.listdir(sql_dir)[0]
    db_abs_file=os.path.abspath(f"{sql_dir}/{db_file}")
    if db_type=="mysql":
        db_name=sql_info_dict["db_name"]
        root_password=sql_info_dict["root_password"]
        db_port=sql_info_dict["db_port"]
        source_db_command=f"/dream/mysql/bin/mysql -uroot -p{root_password} -P {db_port} {db_name} < {db_abs_file}"
        log.logger.debug(f"{source_db_command=}")
        log.logger.info(f"{softname}: 数据导入中, 请稍后...")
        result, msg=common.exec_command(source_db_command, timeout=3600)
        if result:
            if os.path.exists(db_abs_file):
                log.logger.info("清理数据包...")
                os.remove(db_abs_file)
            return normal_code
        else:
            log.logger.error(msg)
            return error_code
    elif db_type=="dameng":
        from_user=sql_info_dict["from_user"].lower()
        to_user=sql_info_dict["to_user"].lower()

        system_user=conf_dict[f"{db_type}_info"]["system_user"]
        dba_user=conf_dict[f"{db_type}_info"]["dba_user"]
        dba_password=conf_dict[f"{db_type}_info"]["dba_password"]
        db_port=conf_dict[f"{db_type}_info"]["db_port"]

        source_db_command=f"chown -R {system_user} {sql_dir} && su -l {system_user} -c 'dimp userid={dba_user}/{dba_password}:{db_port} file={db_abs_file} log=/tmp/{db_type}_{to_user}.log owner={from_user} dummy=Y LOG_WRITE=Y TABLE_EXISTS_ACTION=REPLACE"
        if from_user!=to_user:
            source_db_command=f"{source_db_command} remap_schema={from_user.upper()}:{to_user.upper()}'"
        else:
            source_db_command=f"{source_db_command}'"
        log.logger.debug(f"{source_db_command=}")
        log.logger.info(f"{softname}: 数据导入中, 请稍后...")
        result, msg=common.exec_command(source_db_command, timeout=3600)
        if result:
            if os.path.exists(db_abs_file):
                log.logger.info("清理数据包...")
                os.remove(db_abs_file)
            return normal_code
        else:
            log.logger.error(msg)
            return error_code

def start():
    """启动
    """
    return normal_code

def stop():
    """关闭
    """
    return normal_code

def monitor():
    """监控
    """
    return normal_code

def backup():
    """备份
    """
    backup_version=conf_dict["backup_version"]
    if db_type.lower()=="mysql":
        db_name=sql_info_dict["db_name"]
        db_abs_file=f"{sql_dir}/{db_name}.sql"
        root_password=sql_info_dict["root_password"]
        db_port=sql_info_dict["db_port"]
        dump_db_command=f"mysqldump -uroot -p{root_password} -P {db_port} --set-gtid-purged=OFF {db_name} > {db_abs_file}"
        log.logger.debug(f"{dump_db_command=}")
        log.logger.info(f"{softname}: 数据备份中, 请稍后...")
        result, msg=common.exec_command(dump_db_command, timeout=3600)

    if result:
        log.logger.debug(f"{softname}: 数据压缩, 请稍后...")
        result, msg=common.tar_backup(backup_version, backup_dir, softname, sql_dir, [])
        if os.path.exists(db_abs_file):
            log.logger.info("清理数据包...")
            os.remove(db_abs_file)
        if result:
            return normal_code
        else:
            log.logger.error(msg)
            return error_code
    else:
        log.logger.error(msg)
        return error_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, logger_name="sql")

    located=conf_dict["located"]
    sql_info_dict=conf_dict[f"{softname}_info"]
    db_type=sql_info_dict["db_type"].lower()
    sql_dir=sql_info_dict.get("sql_dir")
    install_dir=sql_dir
    if sql_dir is None:
        sql_dir=f"{located}/{softname}"             # 数据文件的上级目录名称必须与其软件名称相同
        install_dir=located

    if action=="install":
        sys.exit(install())
    elif action=="run":
        sys.exit(run())
    elif action=="start":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(activated_code)
        elif status_value==stopped_code:
            sys.exit(start())
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action=="stop":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(stop())
        elif status_value==stopped_code:
            sys.exit(stopped_code)
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action=="monitor":
        sys.exit(monitor())
    elif action=="backup":
        sys.exit(backup())
    else:
        sys.exit(error_code)

