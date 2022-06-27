#!/usr/bin/env python3
# *-* coding:utf8 *-*
# Date: 2021年 01月 15日 星期五 11:26:15 CST
# sky

import sys, os
workdir=os.path.dirname(sys.path[0])
sys.path[0]=workdir
os.chdir(workdir)

import json, tarfile
import argparse
import pymysql
from libs import common
from libs.env import log_update_level, log_update_file, \
        log_console_level, log_platform_level, \
        db_update_stats_file, remote_pkgs_dir

class DB(object):
    """
    数据库操作
    """
    def __init__(self, db_type, host, port, user, password, db_name, **kwargs):
        self._db_type=db_type
        if self._db_type.lower()=="mysql":
            self.conn=pymysql.connect(host=host, port=port, user=user, passwd=password, db=db_name, charset='utf8mb4')
            self.cursor=self.conn.cursor()

    def exec(self, sql):
        self.cursor.execute(sql)

    def commit(self):
        self.conn.commit()

    def __del__(self):
        self.cursor.close()
        self.conn.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["console", "platform"], help="更新方式")
    parser.add_argument("--type", type=str, choices=["mysql"], help="数据库类型")
    parser.add_argument("--id", type=str, help="项目id")
    parser.add_argument("--sql", type=str, help="数据库更新文件, 以'tar.gz'或'sql'结尾, 须绝对路径")
    parser.add_argument("--host", type=str, help="更新主机. <host1>:<port>")
    parser.add_argument("--user", type=str, help="数据库用户")
    parser.add_argument("--password", type=str, help="数据库密码")
    parser.add_argument("--db", type=str, help="库名")
    args=parser.parse_args()

    mode_level_dict={                   # 定义日志级别
            "file": log_update_level
            }
    if args.mode.lower()=="console":
        mode_level_dict["console"]=log_console_level
        update_mode="file"
        update_stats_addr=db_update_stats_file
    elif args.mode.lower()=="platform":
        mode_level_dict["platform"]=log_platform_level
        update_mode="platform"
        update_stats_addr="平台"
        
    project_id=args.id
    log=common.Logger(mode_level_dict, log_file=log_update_file, project_id=project_id) 

    db_type=args.type
    user=args.user
    password=args.password
    db_name=args.db

    try:
        sql_package=args.sql.strip()
        if not sql_package.startswith("/"):
            log.logger.error("更新包必须为绝对路径")
            sys.exit(1)

        hostname_and_port=args.host.split(":")
        host=hostname_and_port[0]
        try:
            port=int(hostname_and_port[1])
        except IndexError:
            port=3306
    except Exception as e:
        log.logger.error(f"参数解析错误. {str(e)}")
        sys.exit(1)

    
    update_stats_dict={
            "project_id": project_id, 
            "mode": "db_update", 
            "stats":{}
            }

    if sql_package.endswith("tar.gz"):
        try: 
            with tarfile.open(sql_package, "r") as tar:
                log.logger.info(f"解压数据包...")
                log.logger.debug(remote_pkgs_dir)
                sql_file_name=tar.getmembers()[0].name
                tar.extractall(remote_pkgs_dir)
                sql_file=f"{remote_pkgs_dir}/{sql_file_name}"
        except Exception as e:
            log.logger.error(f"解压失败: {str(e)}")
            sys.exit(1)
    elif sql_package.endswith("sql"):
        sql_file=sql_package

    log.logger.info("开始更新:")
    db=DB(db_type, host, port, user, password, db_name)
    log.logger.info(f"'{host}'主机更新:") 

    sql_list=[]
    try:
        log.logger.debug(f"读取数据文件{sql_file}")
        with open(sql_file, "rb") as f:
            log.logger.info(f"数据更新中...")
            for line in f:
                line=line.decode("utf8", "ignore").strip()
                if line=="" or line.startswith("--"):
                    continue
                if line[-1]==";":
                    if len(sql_list)==0:
                        sql_statement=line
                    else:
                        sql_list.append(line)
                        sql_statement=" ".join(sql_list)
                else:
                    sql_list.append(line)
                    continue

                #log.logger.debug(sql_statement)
                db.exec(sql_statement)
                sql_list=[]
            else:
                db.commit()
                flag=True
                log.logger.info(f"'{host}'更新完成\n")
    except Exception as e:
        flag=False
        log.logger.error(f"'{host}'更新失败: {e}")

    update_stats_dict["stats"][host]=flag

    log.logger.debug(f"更新信息: {json.dumps(update_stats_dict)}")
    result, message=common.post_info(update_mode, update_stats_dict, update_stats_addr)
    if result:
        log.logger.info(f"更新信息已生成至'{update_stats_addr}'")
    else:
        log.logger.error(f"更新信息生成失败: {message}")

if __name__ == "__main__":
    main()
