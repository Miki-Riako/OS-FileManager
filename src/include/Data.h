#ifndef FILESYSTEM_DATA_H
#define FILESYSTEM_DATA_H

#include <cstdint>
#include <string>
#include <ctime>
#include <iomanip>
#include "../include/Constraints.h"


class DirectoryItem {
public:
    uint32_t inodeIndex; //本目录项指向的i节点所在的磁盘块号
    char name[FILE_NAME_LENGTH]; //文件名/目录名
};

class Directory { //目录类，一个目录恰好是一个块大小
public:
    DirectoryItem item[DIRECTORY_NUMS]; //32768/128=256
    //从头开始遍历第一个index==0的项为空闲目录项
};


class FileIndex { //文件索引表
public:
    uint32_t index[FILE_INDEX_SIZE]; //数据存放的磁盘块号，4092
    uint32_t next; //下一个索引的磁盘块号，支持大文件，没有为0
};


class INode {
public:
    uint8_t uid; //所属用户ID，默认文件创建者就是文件所有者，拥有该文件所有权限
    uint8_t flag; //高2位00表示文件，01表示目录，10表示软链接，中间3位以rwx格式表示信赖者的访问权限，低3位表示其余用户访问权限
    uint32_t bno; //该文件所在磁盘块号
    char creationTime[25];
    char modifiedTime[25];

    static std::string getCurTime(long long x = std::time(0)) {
        time_t now = x;
        tm* clk = localtime(&now);
        std::stringstream os;
        os << 1900 + clk->tm_year << '-' << std::setw(2) << std::setfill('0') << 1 + clk->tm_mon << '-' << std::setw(2) << std::setfill('0') << clk->tm_mday << ' ';
        os << std::setw(2) << std::setfill('0') << clk->tm_hour << ':' << std::setw(2) << std::setfill('0') << clk->tm_min << ':' << std::setw(2) << std::setfill('0') << clk->tm_sec;
        return os.str();
    }
};


class User {
public:
    uint8_t uid;
    char name[USERNAME_PASWORD_LENGTH];
    char password[USERNAME_PASWORD_LENGTH];
};


class FileSystemCoreInfo { //超级块对象
public:
    uint32_t rootLocation; //根目录所在磁盘块

    uint32_t freeBlockNumber; //空闲块个数
    uint32_t freeBlockStackTop; //空闲块栈的栈顶（栈底根据块大小和磁盘大小可以计算）
    uint16_t freeBlockStackOffset; //空闲块栈栈顶指针所在的块内偏移

    uint32_t avaliableCapacity; //磁盘可用容量

    User users[MAX_USER_NUMS]; //用户列表，最多为8
    uint8_t trustMatrix[MAX_USER_NUMS][MAX_USER_NUMS]; //信赖者矩阵，trustMatrix[i][j]=1代表i信赖j

    uint8_t flag; //超级块修改标记，-1未被修改，0已经被修改
};


#endif //FILESYSTEM_DATA_H
