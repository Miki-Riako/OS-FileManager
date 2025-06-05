#ifndef FILESYSTEM_CONSTRAINTS_H
#define FILESYSTEM_CONSTRAINTS_H

#define DIRECTORY_ITEM_SIZE 128 //目录项的大小，128 bit = 16 Byte
#define BLOCK_SIZE 32768 //块大小，4096 Byte
#define BLOCK_BYTE (BLOCK_SIZE / 8) //块大小，4096 Byte
#define FILE_NAME_LENGTH ((DIRECTORY_ITEM_SIZE - 32) / (8 * sizeof(char))) //文件名最大长度
#define DIRECTORY_NUMS (BLOCK_SIZE / DIRECTORY_ITEM_SIZE) //目录项总项数
#define FILE_INDEX_SIZE (BLOCK_SIZE / 32 - 1) //文件索引表总项数
#define USERNAME_PASWORD_LENGTH 32 //用户名和密码的最大长度
#define MAX_USER_NUMS 8 //最多的用户数

#endif //FILESYSTEM_CONSTRAINTS_H
