#include "Shell.h"

Shell::Shell() {
    user.uid = 0;
    isExit = false;

    //help["Command"] = "Usage               Interpret";
    help["touch"]    = "touch <FILE>                     touch file timestamps";
    help["cat"]      = "cat <FILE>                       concatenate and display files";
    help["rm"]       = "rm <FILE>                        remove files";
    help["rmdir"]    = "rmdir <DIR>                      remove directories";
    help["mkdir"]    = "mkdir <DIR>                      make directories";
    help["cd"]       = "cd <DIR>                         change the working directory";
    help["ls"]       = "ls [-l] [<DIR>]                  list directory contents";
    help["logout"]   = "logout                           exit a login shell";
    help["format"]   = "format                           format disks or tapes";

    help["help"]     = "help                             display information about builtin commands";
    help["clear"]    = "clear                            clear the terminal screen";
    help["exit"]     = "exit                             exit the shell";
    help["chmod"]    = "chmod <FILE> -a|t|o [r][w][x]    change file modes or Access Control Lists";
    help["cp"]       = "cp <SOURCE> <DEST>               copy files and directories";
    help["mv"]       = "mv <SOURCE> <DEST>               move (rename) files";
    help["passwd"]   = "passwd                           update user's authentication tokens";
    help["sudo"]     = "sudo <COMMAND>                   execute a command as another user";
    help["mkuser"]   = "mkuser <USERNAME>                create a new user or update default new user information";
    help["rmuser"]   = "rmuser <USERNAME>                delete a user account and related files";
    help["lsuser"]   = "lsuser                           display a list of system users";
    help["trust"]    = "trust <USERNAME>                 add a user to the trusted list";
    help["distrust"] = "distrust <USERNAME>              remove a user from the trusted list";
    help["vim"]      = "vim <FILE>                       a programmer's file editor";

    userInterface.initialize();
}

std::vector<std::string> Shell::split_path(std::string path) {
    if (path == "~") {
        return std::vector<std::string>{""};
    }

    std::vector<std::string> paths;
    path += '/'; //方便程序处理
    std::string item = "";
    bool occur = false; //判断是否出现路径符号/，多个斜杠算作一个
    for (char ch : path) {
        if (ch == '/') {
            if (!occur) {
                paths.push_back(item);
                item = "";
                occur = true;
            } else {
                continue;
            }
        } else {
            occur = false;
            item += ch;
        }
    }
    return paths;
}

std::pair<bool, std::vector<std::string>> Shell::split_cmd(std::string& cmd) {
    std::vector<std::string> cmds;
    bool isQuote = false;
    std::string item = "";
    for (auto ch : cmd) {
        if (isQuote) {
            if (ch == '\"') {
                cmds.emplace_back(item);
                isQuote = false;
                item = "";
            } else {
                item += ch;
            }
        } else {
            if (ch == '\"') {
                if (!item.empty()) {
                    cmds.emplace_back(item);
                }
                isQuote = true;
                item = "";
            } else if (ch != ' ' && ch != '\t') {
                item += ch;
            } else if (!item.empty()) {
                cmds.emplace_back(item);
                item = "";
            }
        }
    }
    if (isQuote) {
        cmds.clear();
        return std::make_pair(false, cmds);
    }

    if (!item.empty()) {
        cmds.emplace_back(item);
    }
    return std::make_pair(true, cmds);
}

void Shell::exec() {
    std::string input;
    bool valid;
    userInterface.updateDirNow();
    outputPrefix();
    std::getline(std::cin, input);
    std::tie(valid, cmd) = split_cmd(input);

    if (!valid) {
        std::cout << "syntax error:" << " missing terminating \" character" << std::endl;
        return;
    }
    if (cmd.empty()) {
        return;
    }

    std::string cmdType = cmd[0];

    if (cmdType == "sudo") {
        isSudo = true;
        cmd.erase(cmd.begin());
        if (cmd.empty()) {
            cmdType = "";
            std::cout << "sudo: missing command operand" << std::endl;
            return;
        } else {
            cmdType = cmd[0];
        }
        if (!cmd_sudo()) {
            return;
        }
    } else {
        isSudo = false;
    }
    userInterface.setSudoMode(isSudo);
    userInterface.setCurrentCmd(cmdType);

    if (cmdType == "cat") {
        cmd_cat();
    } else if (cmdType == "cd") {
        cmd_cd();
    } else if (cmdType == "chmod") {
        cmd_chmod();
    } else if (cmdType == "clear") {
        cmd_clear();
    } else if (cmdType == "cp") {
        cmd_cp();
    } else if (cmdType == "distrust") {
        cmd_distrust();
    } else if (cmdType == "exit") {
        cmd_exit();
    } else if (cmdType == "format") {
        cmd_format();
    } else if (cmdType == "help") {
        cmd_help();
    } else if (cmdType == "ls") {
        cmd_ls();
    } else if (cmdType == "lsuser") {
        cmd_lsuser();
    } else if (cmdType == "logout") {
        cmd_logout();
    } else if (cmdType == "mkdir") {
        cmd_mkdir();
    } else if (cmdType == "mkuser") {
        cmd_mkuser();
    } else if (cmdType == "mv") {
        cmd_mv();
    } else if (cmdType == "passwd") {
        cmd_passwd();
    } else if (cmdType == "rm") {
        cmd_rm();
    } else if (cmdType == "rmdir") {
        cmd_rmdir();
    } else if (cmdType == "rmuser") {
        cmd_rmuser();
    } else if (cmdType == "touch") {
        cmd_touch();
    } else if (cmdType == "trust") {
        cmd_trust();
    } else if (cmdType == "vim") {
        cmd_vim();
    } else {
        std::cout << cmdType << ": command not found" << std::endl;
    }
}

void Shell::cmd_login() {
    bool debug = true;

    std::string userName;
    std::string password;
    cmd_clear();
    while (1) {
        std::cout << "host@login:Username$ " << std::flush;
        std::cin >> userName;
        if (debug) {
            userName = "root";
        }
        std::cout << "host@login:Password$ " << std::flush;
        std::cin >> password;
        if (debug) {
            password = "123456";
        }

        uint8_t uid = userInterface.userVerify(userName, password);
        if (uid == 0) {
            cmd_clear();
            std::cout << "Access denied. " << "Please check username or password." << std::endl;
        }
        else {
            userInterface.getUser(uid, &user);
            break;
        }
    }
    cmd_clear();
    std::getchar();
    curPath.clear();
}

void Shell::cmd_logout() {
    if (cmd.size() > 1) {
        std::cout << "logout: too much arguments" << std::endl;
        return;
    }
    userInterface.logout();
    user.uid = 0;
}

void Shell::cmd_exit() {
    if (cmd.size() > 1) {
        std::cout << "exit: too much arguments" << std::endl;
        return;
    }
    userInterface.logout();
    user.uid = 0;
    isExit = true;
}

void Shell::cmd_cd() {
    if (cmd.size() > 2) {
        std::cout << "cd: too much arguments" << std::endl;
        return;
    }
    if (cmd.size() == 1) {
        return;
    }

    if (!cmd[1].empty() && cmd[1][0] == '~') {
        cmd[1] = cmd[1].substr(1);
    }
    std::vector<std::string> src = split_path(cmd[1]);
    bool ok = true;
    for (std::string& item : src) {
        if (item == "") {
            userInterface.goToRoot();
            curPath.clear();
        } else if (item == ".") {
            continue;
        } else if (item == "..") {
            if (userInterface.cd(user.uid, item, cmd[1]).first && !curPath.empty()) {
                curPath.pop_back();
            } else {
                break;
            }
        } else {
            if (userInterface.cd(user.uid, item, cmd[1]).first) {
                curPath.push_back(item);
            } else {
                break;
            }
        }
    }
}

void Shell::cmd_ls() {
    if (cmd.size() > 3) {
        std::cout << "ls: too much arguments" << std::endl;
        return;
    }

    if (cmd.size() == 1) {
        userInterface.ls(user.uid, false, std::string());
    }
    else if (cmd.size() == 2) {
        if (cmd[1] == "-l") {
            userInterface.ls(user.uid, true, std::string());
        } else {
            std::vector<std::string> src = split_path(cmd[1]);
            if (src.empty()) {
                std::cout << "ls: missing operand" << std::endl;
                return;
            }
            userInterface.ls(user.uid, false, src, cmd[1]);
        }
    } else {
        if (cmd[1] == "-l") {
            std::vector<std::string> src = split_path(cmd[2]);
            if (src.empty()) {
                std::cout << "ls: missing operand" << std::endl;
                return;
            }
            userInterface.ls(user.uid, true, src, cmd[2]);
        } else if (cmd[2] == "-l") {
            std::vector<std::string> src = split_path(cmd[1]);
            if (src.empty()) {
                std::cout << "ls: missing operand" << std::endl;
                return;
            }
            userInterface.ls(user.uid, true, src, cmd[1]);
        } else {
            std::cout << "ls: too much arguments" << std::endl;
        }
    }
}

void Shell::cmd_touch() {
    if (cmd.size() < 2) {
        std::cout << "touch: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "touch: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "touch: missing file operand" << std::endl;
        return;
    }
    std::string fileName = src.back();
    if (fileName.length() >= FILE_NAME_LENGTH) {
        std::cout << "touch: too long file name" << std::endl;
        return;
    }
    src.pop_back();
    if (!src.empty()) {
        userInterface.touch(user.uid, src, fileName, cmd[1]);
    } else {
        userInterface.touch(user.uid, fileName, cmd[1]);
    }
}

void Shell::cmd_cat() {
    if (cmd.size() < 2) {
        std::cout << "cat: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "cat: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "cat: missing file operand" << std::endl;
        return;
    }
    std::string fileName = src.back();
    src.pop_back();
    if (!src.empty()) userInterface.cat(user.uid, src, fileName, cmd[1]);
    else userInterface.cat(user.uid, fileName, cmd[1]);
}

void Shell::cmd_mv() {
    if (cmd.size() < 3) {
        std::cout << "mv: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 3) {
        std::cout << "mv: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "mv: missing file operand" << std::endl;
        return;
    }
    std::vector<std::string> des = split_path(cmd[2]);
    if (des.empty()) {
        std::cout << "mv: missing file operand" << std::endl;
        return;
    }
    userInterface.mv(user.uid, src, des, cmd[1], cmd[2]);
}

void Shell::cmd_cp() {
    if (cmd.size() < 3) {
        std::cout << "cp: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 3) {
        std::cout << "cp: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "cp: missing file operand" << std::endl;
        return;
    }
    std::vector<std::string> des = split_path(cmd[2]);
    if (des.empty()) {
        std::cout << "cp: missing file operand" << std::endl;
        return;
    }
    userInterface.cp(user.uid, src, des, cmd[1], cmd[2]);
}

void Shell::cmd_rm() {
    if (cmd.size() < 2) {
        std::cout << "rm: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "rm: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "rm: missing file operand" << std::endl;
        return;
    }
    std::string fileName = src.back();
    src.pop_back();
    if (!src.empty()) {
        userInterface.rm(user.uid, src, fileName, cmd[1]);
    } else {
        userInterface.rm(user.uid, fileName, cmd[1]);
    }
}

void Shell::cmd_mkdir() {
    if (cmd.size() < 2) {
        std::cout << "mkdir: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "mkdir: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "mkdir: missing operand" << std::endl;
        return;
    }
    std::string dirName = src.back();
    if (dirName.length() >= FILE_NAME_LENGTH) {
        std::cout << "mkdir: too long directory name" << std::endl;
        return;
    }
    src.pop_back();
    if (!src.empty()) {
        userInterface.mkdir(user.uid, src, dirName, cmd[1]);
    } else {
        userInterface.mkdir(user.uid, dirName, cmd[1]);
    }
}

void Shell::cmd_rmdir() {
    if (cmd.size() < 2) {
        std::cout << "rmdir: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "rmdir: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "rmdir: missing operand" << std::endl;
        return;
    }
    std::string dirName = src.back();
    src.pop_back();
    if (!src.empty()) {
        userInterface.rmdir(user.uid, src, dirName, cmd[1]);
    } else {
        userInterface.rmdir(user.uid, dirName, cmd[1]);
    }
}

bool Shell::cmd_sudo() {
    std::cout << "[sudo] password for " << user.name << ": " << std::flush;
    std::string password;
    std::cin >> password;
    std::cin.ignore();

    uint8_t checkUid = userInterface.userVerify(user.name, password);
    if (!checkUid) {
        std::cout << "Password verification " << RED << "failed" << RESET << std::endl;
        return false;
    }
    else if (checkUid != user.uid) {
        std::cout << "sudo: System error" << std::endl;
        return false;
    }
    else {
        std::cout << "Verification successful" << std::endl;
        return true;
    }
}

void Shell::cmd_format() {
    if (cmd.size() > 1) {
        std::cout << "format: too much arguments" << std::endl;
        return;
    }
    userInterface.logout();
    userInterface.format();
    curPath.clear();
    user.uid = 0;
}

void Shell::cmd_chmod() {
    //chmod <file> -ato rwx
    if (cmd.size() < 3) {
        std::cout << "chmod: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 4) {
        std::cout << "chmod: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "chmod: missing operand" << std::endl;
        return;
    }
    if (cmd[2] != "-a" && cmd[2] != "-t" && cmd[2] != "-o") {
        std::cout << "chmod: " << RED << "invalid " << RESET << "mode: '" << cmd[2] << "'" << std::endl;
        return;
    }
    std::string access(3, '-');
    if (cmd.size() == 4) {
        std::string tmp = cmd[3];
        if (tmp.find('r') != std::string::npos) {
            access[0] = 'r';
            tmp.erase(tmp.find('r'), 1);
        }
        if (tmp.find('w') != std::string::npos) {
            access[1] = 'w';
            tmp.erase(tmp.find('w'), 1);
        }
        if (tmp.find('x') != std::string::npos) {
            access[2] = 'x';
            tmp.erase(tmp.find('x'), 1);
        }
        if (!tmp.empty()) {
            std::cout << "chmod: " << RED << "invalid " << RESET << "access: '" << cmd[3] << "'" << std::endl;
            return;
        }
    }

    std::string dirName = src.back();
    src.pop_back();
    if (!src.empty()) {
        userInterface.chmod(user.uid, src, dirName, cmd[2], access, cmd[1]);
    } else {
        userInterface.chmod(user.uid, dirName, cmd[2], access, cmd[1]);
    }
}

void Shell::cmd_mkuser() {
    if (cmd.size() < 2) {
        std::cout << "mkuser: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "mkuser: too much arguments" << std::endl;
        return;
    }

    std::string name = cmd[1];
    if (name.length() >= USERNAME_PASWORD_LENGTH) {
        std::cout << "mkuser: too long user name" << std::endl;
        return;
    }
    userInterface.mkuser(user.uid, name);
}

void Shell::cmd_rmuser() {
    if (cmd.size() < 2) {
        std::cout << "rmuser: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "rmuser: too much arguments" << std::endl;
        return;
    }

    std::string name = cmd[1];
    userInterface.rmuser(user.uid, name);
}

void Shell::cmd_lsuser() {
    if (cmd.size() > 1) {
        std::cout << "lsuser: too much arguments" << std::endl;
        return;
    }
    userInterface.lsuser();
}

void Shell::cmd_passwd() {
    if (cmd.size() > 1) {
        std::cout << "passwd: too much arguments" << std::endl;
        return;
    }
    userInterface.passwd(user.uid, user.name);
}

void Shell::cmd_trust() {
    if (cmd.size() < 2) {
        std::cout << "trust: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "trust: too much arguments" << std::endl;
        return;
    }

    std::string name = cmd[1];
    userInterface.trust(user.uid, user.name, name);
}

void Shell::cmd_distrust() {
    if (cmd.size() < 2) {
        std::cout << "distrust: missing operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "distrust: too much arguments" << std::endl;
        return;
    }

    std::string name = cmd[1];
    userInterface.distrust(user.uid, user.name, name);
}

void Shell::cmd_help() {
    if (cmd.size() > 2) {
        std::cout << "cd: too much arguments" << std::endl;
        return;
    }

    if (cmd.size() == 1) { //单独执行help，表示输出所有命令
        std::cout << "Usage                            Interpret" << std::endl;
        std::cout << "__________________________________________" << std::endl;
        for (auto [_, inform] : help) {
            std::cout << inform << std::endl;
        }
    } else if (help.count(cmd[1])) {
        std::cout << "Usage                            Interpret" << std::endl;
        std::cout << "__________________________________________" << std::endl;
        std::cout << help[cmd[1]] << std::endl;
    } else {
        std::cout << "help: " << cmd[1] << ": command not found" << std::endl;
    }
}

void Shell::cmd_clear() {
    system("cls");
}

void Shell::cmd_vim() {
    if (cmd.size() < 2) {
        std::cout << "vim: missing file operand" << std::endl;
        return;
    }
    if (cmd.size() > 2) {
        std::cout << "vim: too much arguments" << std::endl;
        return;
    }

    std::vector<std::string> src = split_path(cmd[1]);
    if (src.empty()) {
        std::cout << "vim: missing file operand" << std::endl;
        return;
    }
    std::string fileName = src.back();
    if (fileName.length() >= FILE_NAME_LENGTH) {
        std::cout << "vim: too long file name" << std::endl;
        return;
    }
    src.pop_back();
    if (!src.empty()) userInterface.vim(user.uid, src, fileName, cmd[1]);
    else userInterface.vim(user.uid, fileName, cmd[1]);
}

void Shell::outputPrefix() {
    std::cout << "OSFileSystem@" << user.name << ":" << "~";
    for (const auto& s : curPath) {
        std::cout << "/" << s;
    }
    std::cout << "$ ";
}
