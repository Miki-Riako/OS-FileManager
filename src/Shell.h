#ifndef FILESYSTEM_SHELL_H
#define FILESYSTEM_SHELL_H

#include <string>
#include <map>
#include <iostream>
#include <tuple>
#include <sstream>
#include <vector>

#include "CommandLineInterface.h"
#include "include/Data.h"

class Shell {
public:
    bool debug = true;
    Shell();

    //根据part分割str
    std::vector<std::string> split_path(std::string path); //路径划分 data/ztr/sghn->data   ztr    sghn
    std::pair<bool, std::vector<std::string>> split_cmd(std::string& path); //cmd划分  cp /data1/1.txt /data2/1.txt->cp  /data1/1.txt     /data2/1.txt
    bool isExit; //是否退出标记

    //界面主程序
    void exec(); //退出终端的具体实现
    void cmd_cat();
    void cmd_cd();
    void cmd_clear();
    void cmd_chmod();
    void cmd_cp();
    void cmd_distrust();
    void cmd_echo();
    void cmd_exit();
    void cmd_format();
    void cmd_help();
    void cmd_login();
    void cmd_logout();
    void cmd_ls();
    void cmd_lsuser();
    void cmd_mkdir();
    void cmd_mkuser();
    void cmd_mv();
    void cmd_passwd();
    void cmd_rm();
    void cmd_rmdir();
    void cmd_rmuser();
    bool cmd_sudo();
    void cmd_touch();
    void cmd_trust();

    void cmd_vim(); //vim命令处理程序

    void outputPrefix(); //输出当前文件系统的命令提示符

private:
    std::vector<std::string> cmd;                  //用户输入的整行命令
    User user;                                     //当前登录用户
    bool isSudo;                                   //是否是超管状态
    CommandLineInterface userInterface;            //用户接口
    std::vector<std::string> curPath;              //当前从根目录开始的路径
    std::map<std::string, std::string> help;       //帮助文档
};

#endif //FILESYSTEM_SHELL_H
