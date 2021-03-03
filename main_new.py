#!../ext/python3/bin/python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys
#import getopt
import argparse
from textwrap import dedent
from libs import deploy


def print_usage_info():
    usage_info=dedent(f"""
        Usage: {sys.argv[0]} OPTIONS [COMMAND]

        Options:
            -t, --text command          以文本方式安装
            -g, --graphics              以图形方式安装
            -p, --paltform command      以平台方式安装

        Commands:
            init                       集群初始化
            install                    集群安装
            start                      集群启动
            update [package]           项目数据部署/更新
            deploy                     集群部署(install, start, update)


    """)
    return usage_info

def main():
    choices=["init", "install", "run", "start", "stop", "update", "deploy"]
    parser=argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", type=str, choices=choices, help="阶段")
    group.add_argument("-p", type=str, choices=choices, help="阶段")
    group.add_argument("-g", type=str, help="project_id")

    parser.add_argument("-f", type=str, help="指定项目包文件路径")
    parser.add_argument("-i", type=str, help="指定项目id")
    args=parser.parse_args()

    if args.t is not None:
        d=deploy.text_deploy()
        arg=args.t
        if arg=="init":
            d.init(args[0])
        elif arg=="install":
            d.install()
        elif arg=="start":
            d.start()
        elif arg=="update":
            d.update(args)
        elif arg=="deploy":
            d.deploy(args[0])
    if args.g is not None:
        program_id=args.g
        d=deploy.graphics_deploy(program_id)
        d.show()
    if args.p is not None:
        program_id=args.i
        d=deploy.platform_deploy(program_id)
        arg=args.p
        if arg=="init":
            result_dict=d.init()
        elif arg=="install":
            program_pkg=args.f
            result_dict=d.install(program_pkg)
        elif arg=="run":
            result_dict=d.run()
        elif arg=="start":
            result_dict=d.start()
        elif arg=="update":
            program_pkg=args.f
            result_dict=d.update(program_pkg)
        elif arg=="deploy":
            program_pkg=args.f
            result_dict=d.deploy(program_pkg)
        d.generate_info("platform", result_dict)


    """
    try:
        options, args=getopt.getopt(sys.argv[1:], "t:p:gh", ["text=", "platform=", "graphics", "help"])
    except getopt.GetoptError:
        print(print_usage_info())
        sys.exit(1)

    print(f"{options=}, {args=}")

    if len(options)==0:
        print(print_usage_info())
        sys.exit(1)

    #conf_file="./config/conf.json"
    #init_file="./config/init.json"
    #arch_file="./config/arch.json"
    #project_file="./config/project"

    for opt, arg in options:
        if opt in ("-g", "--graphics"):
            d=deploy.graphics_deploy()
            d.show()
            break
        elif opt in ("-t", "--text"):
            d=deploy.text_deploy()
            if arg=="init":
                d.init(args[0])
            elif arg=="install":
                d.install()
            elif arg=="start":
                d.start()
            elif arg=="update":
                d.update(args)
            elif arg=="deploy":
                d.deploy(args[0])
            else:
                print(print_usage_info())
            break
        elif opt in ("-p", "--platform"):
            d=deploy.platform_deploy(args[0])
            if arg=="init":
                d.init()
            elif arg=="install":
                d.install()
            elif arg=="start":
                d.start()
            elif arg=="update":
                d.update(args)
            elif arg=="deploy":
                d.deploy()
            else:
                print(print_usage_info())
            break
        elif opt in ("-h", "--help"):
            print(print_usage_info())
        else:
            print(print_usage_info())
    """

if __name__ == "__main__":
    main()
