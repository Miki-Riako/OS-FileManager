#include "Shell.h"

Shell::Shell() {
    user.uid = 0;
    isExit = false;

    help["touch"]    = "touch <FILE>                     touch file timestamps";
    help["cat"]      = "cat <FILE>                       concatenate and display files";
    help["echo"]     = "echo <STRING> [>|>> <FILE>]      display a line of text or redirect output";
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
        std::cout << "syntax error: missing terminating \" character" << std::endl;
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
    } else if (cmdType == "echo") {
        cmd_echo();
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
            std::cout << "Access denied. Please check username or password." << std::endl;
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

    if (!cmd[1].empty() && cmd[1][0] == '~') {
        cmd[1] = cmd[1].substr(1);
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
        std::cout << "Password verification failed" << std::endl;
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
        std::cout << "chmod: invalid mode: '" << cmd[2] << "'" << std::endl;
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
            std::cout << "chmod: invalid access: '" << cmd[3] << "'" << std::endl;
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

void Shell::cmd_echo() {
    if (cmd.size() == 2) {
        std::cout << cmd[1] << std::endl; // 打印到终端，std::endl会添加换行
    } else if (cmd.size() == 4) { // 形式: echo "content" > file 或 echo "content" >> file
        if (cmd[2] != ">" && cmd[2] != ">>") { // 检查重定向运算符是否有效
            std::cout << "echo: syntax error: unrecognized redirect operator '" << cmd[2] << "'" << std::endl;
            return;
        }
        std::string content_to_process = cmd[1]; // 用户输入的待写入内容
        std::string target_file_path = cmd[3]; // 目标文件路径
        bool append = (cmd[2] == ">>");       // 是否是追加模式
        // 解析文件路径和文件名
        std::vector<std::string> path_parts = split_path(target_file_path);
        // 修正路径解析，确保即使是根目录或当前目录的空路径也有效
        if (path_parts.empty() || (path_parts.size() == 1 && path_parts[0].empty() && target_file_path != "~")) {
            std::cout << "echo: invalid file path '" << target_file_path << "'" << std::endl;
            return;
        }
        std::string fileName = path_parts.back(); // 提取文件名
        if (path_parts.size() > 1 || (path_parts.size() == 1 && !path_parts[0].empty())) { // 只有在path_parts不是空的或者不是只包含一个空字符串（即根目录或当前目录）时才pop_back
            path_parts.pop_back();                     // path_parts 现在只包含父目录部分
        } else { // Handle root/current directory file directly when path_parts is initially just {""} or {"~"}
            path_parts.clear(); // Ensure it's truly empty if it represents current dir for clarity
        }
        if (fileName.length() >= FILE_NAME_LENGTH) { // 检查文件名长度
            std::cout << "echo: too long file name '" << fileName << "'" << std::endl;
            return;
        }
        std::string final_content_for_vim;
        std::string original_creation_time;
        if (append) { // 如果是追加模式 (>>)
            std::tuple<bool, std::string, std::string> existing_content_tuple; // tuple: {success, content, creationTime}
            std::get<0>(existing_content_tuple) = false; // Flag to indicate we want content back
            bool cat_success;
            if (path_parts.empty()) { // 文件在当前目录或根目录
                cat_success = userInterface.cat(user.uid, fileName, target_file_path, &existing_content_tuple);
            } else { // 文件在指定路径
                cat_success = userInterface.cat(user.uid, path_parts, fileName, target_file_path, &existing_content_tuple);
            }
            if (!cat_success) {
                // 如果cat失败（例如文件不存在、权限不足、是目录等），cat会打印错误信息。
                // 特别是 "No such file or directory" 错误，在追加模式下，我们不允许创建新文件。
                std::cout << "echo: " << target_file_path << ": No such file or directory for append. Use '>' to create and write." << std::endl;
                return;
            }
            std::string existing_content = std::get<1>(existing_content_tuple);
            original_creation_time = std::get<2>(existing_content_tuple); // 保留原有文件的创建时间
            // 确保现有内容以换行符结尾，除非它是空文件。
            if (!existing_content.empty() && existing_content.back() != '\n') {
                existing_content += '\n';
            }
            // 将新内容追加到原有内容之后，并确保新内容也以换行符结尾。
            final_content_for_vim = existing_content + content_to_process + "\n";
        } else { // 如果是覆盖模式 (>)
            // 写入的内容就是用户输入的，并确保以换行符结尾。
            final_content_for_vim = content_to_process + "\n";
            original_creation_time = INode::getCurTime(); // 新文件或覆盖文件，创建时间设置为当前
        }
        // ---------- 写入文件 ----------
        std::tuple<bool, std::string, std::string> write_content_tuple;
        std::get<0>(write_content_tuple) = false; // 标记：这是传入的内容
        std::get<1>(write_content_tuple) = final_content_for_vim;
        std::get<2>(write_content_tuple) = original_creation_time; // 传递文件创建时间
        bool write_success;
        if (path_parts.empty()) { // 文件在当前目录或根目录
            write_success = userInterface.vim(user.uid, fileName, target_file_path, &write_content_tuple);
        } else { // 文件在指定路径
            write_success = userInterface.vim(user.uid, path_parts, fileName, target_file_path, &write_content_tuple);
        }
        if (!write_success) { // vim 内部会打印详细的错误信息（例如权限不足、路径不存在等），所以这里无需重复打印。
            return;
        }
    } else { // 参数数量不正确
        std::cout << "echo: invalid number of arguments." << std::endl;
        std::cout << "Usage: echo <TEXT>           (print to terminal)" << std::endl;
        std::cout << "       echo <TEXT> > <FILE>  (overwrite file)" << std::endl;
        std::cout << "       echo <TEXT> >> <FILE> (append to file)" << std::endl;
    }
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
    std::cout << "OSFileSystem@" << user.name << ":~";
    for (const auto& s : curPath) {
        std::cout << "/" << s;
    }
    std::cout << "$ ";
}
