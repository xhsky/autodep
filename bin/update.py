#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# 2021-01-13 14:51:02
# sky

import sys, json, os, time
import tarfile, shutil
from libs import common
from libs.env import log_remote_level, update_package_dir, rollback_dir, normal_code, error_code

def code_update(args_dict, log):
    """用于本地代码更新
    args_dict={
        "hosts": ["node1"], 
        "type": "jar", 
        "dest": "str", 
        ...
        "pkg_file": "str", 
        "delete_flag": True|False,          # 是否删除原项目
    }
    """
    code_type=args_dict.get("type")
    pkg_file=args_dict.get("pkg_file")
    dest=args_dict.get("dest")

    if not os.path.exists(dest):
        try:
            log.logger.info(f"建立目录{dest}")
            os.makedirs(dest, exist_ok=1)
        except Exception as e:
            log.logger.error(f"无法建立目录: {str(e)}")
            return error_code
    try:
        if code_type=="frontend":
            log.logger.debug("开始前端更新...")
            with tarfile.open(pkg_file, "r", encoding="utf8") as tar:
                #for i in tar.getmembers():
                #    code_dir_name=i.name
                #    break
                #code_dir_abs=f"{dest}/{code_dir_name}"
                #if os.path.exists(code_dir_abs):
                #    time_format=time.strftime("%Y%m%d%H%M%S", time.localtime())
                #    save_dir=f"{code_saved_remote_dir}/{code_dir_name}_{time_format}"
                #    save_file=f"{save_dir}.tar.gz"
                #    log.logger.info(f"备份'{code_dir_abs}'至'{save_file}'...")
                #    with tarfile.open(save_file, "w:gz", encoding="utf8") as s_tar:
                #        s_tar.add(code_dir_abs)
                #    #shutil.move(code_dir_abs, save_dir)
                if args_dict["delete_flag"]:
                    for i in tar.getmembers():
                        code_dir_name=i.name
                        break
                    code_dir_abs=f"{dest}/{code_dir_name}"
                    log.logger.debug(f"删除原目录{code_dir_abs}")
                    shutil.rmtree(code_dir_abs)
                log.logger.debug(f"解压'{pkg_file}'至'{dest}'")
                tar.extractall(dest)
        else: 
            log.logger.debug("开始后端更新...")
            propertiesPath=args_dict["propertiesPath"]
            shutil.move(pkg_file, f"{dest}/{pkg_file.split('/')[-1]}")
            shutil.move(propertiesPath, f"{dest}/application-prod.{propertiesPath.split('.')[-1]}")
        if os.path.exists(pkg_file):
            log.logger.info("清理项目包...")
            os.remove(pkg_file)
    except Exception as e:
        log.logger.error(f"更新失败: {str(e)}")
        return error_code
    return normal_code

def db_update(args_dict, log):
    """用于数据库更新
    args_dict={
        "host": "node1", 
        "password": "str", 
        "type": "mysql", 
        "db": "str", 
        ...
        "pkg_file": "str", 
        "delete_flag": True|False,          # 是否删除原项目
    }
    """

    log.logger.info("开始数据更新, 请稍后...")
    db_type=args_dict["type"]
    pkg_file=args_dict.get("pkg_file")
    try:
        log.logger.debug(f"解压'{pkg_file}'至'{update_package_dir}'")
        with tarfile.open(pkg_file, "r", encoding="utf8") as tar:
            for i in tar.getmembers():
                db_file_name=i.name
                break
            tar.extractall(update_package_dir)
        db_file=f"{update_package_dir}/{db_file_name}"
        if db_type=="mysql":
            password=args_dict["password"]
            db_name=args_dict["db"]
            if args_dict["delete_flag"]:
                drop_db_command="mysqladmin -uroot -p{password} -f drop {db_name}"
                log.logger.debug(f"{drop_db_command=}")
                result, msg=common.exec_command(drop_db_command, timeout=3600)
                if not result:
                    log.logger.error(msg)
                    return error_code
            source_db_command=f"mysql -uroot -p{password} {db_name} < {db_file}"
            log.logger.debug(f"{source_db_command=}")
            result, msg=common.exec_command(source_db_command, timeout=3600)
            if result:
                return normal_code
            else:
                log.logger.error(msg)
                return error_code
        else:
            log.logger.error(f"{db_type}类型不支持")
            return error_code

        if os.path.exists(db_file):
            log.logger.info("清理更新包...")
            os.remove(db_file)
    except Exception as e:
        log.logger.error(f"更新失败: {str(e)}")
        return error_code

def code_backup(args_dict, log):
    """代码备份
    args_dict={
        ...
        ...
        "type": jar|frontend|war|dir
        "backup_name": str
    }
    """
    code_type=args_dict["type"]
    dest=args_dict["dest"]
    backup_name=args_dict["backup_name"]
    if code_type=="jar":
        propertiesPath=args_dict["propertiesPath"]
        try:
            shutil.copyfile(f"{dest}/{backup_name}", f"{rollback_dir}/{backup_name}")
            shutil.copyfile(f"{dest}/application-prod.{propertiesPath.split('.')[-1]}", f"{rollback_dir}/{propertiesPath}")
        except Exception as e:
            log.logger.error(str(e))
            return error_code
    elif code_type=="frontend":
        try:
            with tarfile.open(f"{rollback_dir}/{backup_name}", "w:gz", encoding="utf8") as tar:
                tar.add(dest)
        except Exception as e:
            log.logger.error(str(e))
            return error_code
    return normal_code

def db_backup(args_dict, log):
    """数据库备份
    """
    db_type=args_dict["type"]
    backup_name=args_dict["backup_name"]
    if db_type.lower()=="mysql":
        root_password=args_dict["password"]
        db_name=args_dict["db"]
        db_file=f"{rollback_dir}/{db_name}"
        command=f"mysqldump -uroot -p'{root_password}' --set-gtid-purged=off {db_name} > {db_file}"
        log.logger.debug(f"{command=}")
        result, msg=common.exec_command(command, timeout=3600)
        if result:
            db_file_size=os.path.getsize(db_file)
            if  db_file_size < 1024 * 1024 * 10:
                log.logger.warning(f"导出文件过小, {db_file}: {common.format_size(db_file_size)}")
                return error_code
            db_gz_file=f"{rollback_dir}/{backup_name}"
            try:
                with tarfile.open(db_gz_file, "w:gz", encoding="utf8") as tar:
                    tar.add(db_file)
            except Exception as e:
                log.logger.error(str(e))
                return error_code
        else:
            log.logger.error(msg)
            return error_code
    else:
        pass
    return normal_code

def main():
    action, args_json=sys.argv[1:]
    args_dict=json.loads(args_json)
    log=common.Logger({"remote": log_remote_level})

    if not os.path.exists(rollback_dir):
        os.makedirs(rollback_dir, exist_ok=1)
    func_dict={
            "code_update": code_update, 
            "db_update": db_update, 
            "code_backup": code_backup, 
            "db_backup": db_backup
            }

    sys.exit(func_dict[action](args_dict, log))

if __name__ == "__main__":
    main()
