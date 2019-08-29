# coding=utf-8

# 自动打包工具
# Author: ZinkLu
# Date: 2019/3/26

# example json

"""
{
    "NOTES": "子文件列表元素个数应该与命令列表元素个数相同",   # 不会被解析

    "base_path": "/Users/zinklu/Downloads/standard",  # 根目录

    "build_list": ["command_list1", ],  # 需要执行的命令列表, 只会执行里面的命令
    "modules":{  # modules 为一个命令组对象
        "command_list1": [
            {
                "file_path": "src_foo_dir",  # 根目录下的目录
                "command_list": ["npm i", "gulp -t crm -b", "rm -rf node_modules"]  # 在改文件夹下执行的命令, 依次执行
            },
            {
                "file_path": "src_foo_dir/src_bar_dir",  # 切换到下一个文件夹, 继续执行command_list, 文件夹必须是相对base_path的路径
                "command_list": ["npm i", "npm run build", "rm -rf node_modules"]
            },
            ...
        ],

        # 由于build_list没有command_list2, 因此不会执行里面任何的命令
        "command_list2": [
            ...
        ]
    }
}
"""

from six.moves import input
import time
import os
import sys
import json
import time


def main(json_content):
    timmer1 = time.time()
    base_path = json_content.get('base_path')  # type: string
    build_list = json_content.get('build_list')  # type: list
    modules = json_content.get('modules')  # type: list

    if not os.path.isdir(base_path):
        print("Can't find root dir: %s" % base_path)
        return

    for bulid_target in build_list:
        files_commands = modules.get(bulid_target, None)

        if files_commands is None:
            print("===========Can't find module to build%s ==========" %
                  bulid_target)
            continue

        print("==========building %s ==========" % bulid_target)
        print("\n" * 2)
        for file_command in files_commands:
            file_path = file_command.get('file_path', "")
            command_list = file_command.get('command_list', [])

            file_path = os.path.join(base_path, file_path)
            try:
                os.chdir(file_path)
            except Exception as e:
                print("Wrong file path %s" % file_path)
                continue

            # zip_iter = zip(file_path, command_list)

            print("==========Processing dir %s=========" % file_path)
            for command in command_list:
                time.sleep(0.5)
                print(
                    "============Executing %s , press Ctrl+C to stop ==========" % command)
                res = os.system(command)
                if res == 0:
                    print(
                        "================%s executed successed==============" % command)
                    print("\n")
                else:
                    print(
                        "================%s: executed failed================" % command)
                    print("\n")
                    while True:
                        to_be_continue = input("Continue? Y/N")
                        if to_be_continue.lower() not in ('y', 'n'):
                            print("Wrong choice ..")
                            continue
                        break
                    if to_be_continue == 'y':
                        continue
                    else:
                        break

        print("\n\n\n\n")

    finish_task()
    print("All task finished, taking %0.2f" % (time.time() - timmer1))


def finish_task():
    s = """
     __  __  ___  ____   ____   ___   ___   _   _    ____   ___   __  __  ____   _      _____  _____  _____  _
    |  \/  ||_ _|/ ___| / ___| |_ _| / _ \ | \ | |  / ___| / _ \ |  \/  ||  _ \ | |    | ____||_   _|| ____|| |
    | |\/| | | | \___ \ \___ \  | | | | | ||  \| | | |    | | | || |\/| || |_) || |    |  _|    | |  |  _|  | |
    | |  | | | |  ___) | ___) | | | | |_| || |\  | | |___ | |_| || |  | ||  __/ | |___ | |___   | |  | |___ |_|
    |_|  |_||___||____/ |____/ |___| \___/ |_| \_|  \____| \___/ |_|  |_||_|    |_____||_____|  |_|  |_____|(_)
    """
    print(s)


if __name__ == "__main__":
    command = sys.argv
    path = command[1]
    print(path)
    if not os.path.isfile(path):
        print(u'Wrong file path ')
    with open(path) as f:
        content = f.read()
        json_content = json.loads(content)

    main(json_content)
