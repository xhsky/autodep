#!../ext/python3/bin/python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys, os
import argparse
from textwrap import dedent
from libs import deploy

def main():
    choices=["init", "install", "run", "start", "stop", "update", "deploy", "monitor", "check"]
    parser=argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", type=str, choices=choices, help="阶段")
    group.add_argument("-p", type=str, choices=choices, help="阶段")
    group.add_argument("-g", help="图形方式启动", action="store_true")

    #parser.add_argument("-f", type=str, help="指定项目包文件路径")
    parser.add_argument("-i", type=str, help="指定项目id")
    args=parser.parse_args()

    if os.getuid() != 0:
        print("Error: 该程序需要用root用户启动")
        return 

    if args.t is not None:
        d=deploy.text_deploy()
        arg=args.t
        if arg=="stop":
            d.stop()
        elif arg=="start":
            d.start()
        elif arg=="update":
            d.update(args)
        elif arg=="deploy":
            d.deploy()
    elif args.p is not None:
        program_id=args.i
        d=deploy.platform_deploy(program_id)
        arg=args.p
        if arg=="init":
            result_dict=d.init()
        elif arg=="install":
            #program_pkg=args.f
            #result_dict=d.install(program_pkg)
            result_dict=d.install()
        elif arg=="run":
            result_dict=d.run()
        elif arg=="start":
            result_dict=d.start()
        elif arg=="stop":
            result_dict=d.stop()
        elif arg=="update":
            #program_pkg=args.f
            #result_dict=d.update(program_pkg)
            result_dict=d.update()
        elif arg=="deploy":
            #program_pkg=args.f
            #result_dict=d.deploy(program_pkg)
            result_dict=d.deploy()
        elif arg=="monitor":
            result_dict=d.monitor()
        elif arg=="check":
            result_dict=d.check()
        d.generate_info("platform_info", result_dict)
    elif args.g is not None:
        d=deploy.graphics_deploy()
        d.show()

if __name__ == "__main__":
    main()
