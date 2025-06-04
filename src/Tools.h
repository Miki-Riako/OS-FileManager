#ifndef FILESYSTEM_TOOLS_H
#define FILESYSTEM_TOOLS_H

//彩色化输出printf方式
#define printf_grey(fmt, args...) \
    printf("\e[1;30m" fmt "\e[0m", ## args)

#define printf_red(fmt, args...) \
    printf("\e[1;31m" fmt "\e[0m", ## args)

#define printf_green(fmt, args...) \
    printf("\e[1;32m" fmt "\e[0m", ## args)

#define printf_yellow(fmt, args...) \
    printf("\e[1;33m" fmt "\e[0m", ## args)

#define printf_blue(fmt, args...) \
    printf("\e[1;34m" fmt "\e[0m", ## args)

#define printf_purple(fmt, args...) \
    printf("\e[1;35m" fmt "\e[0m", ## args)

#define printf_light_blue(fmt, args...) \
    printf("\e[1;36m" fmt "\e[0m", ## args)

#define printf_white(fmt, args...) \
    printf("\e[1;37m" fmt "\e[0m", ## args)

// //彩色化输出cout方式
// #define RESET "
// #define BLACK ""   /* Black */
// #define RED ""     /* Red */
// #define GREEN ""   /* Green */
// #define YELLOW ""  /* Yellow */
// #define BLUE ""    /* Blue */
// #define MAGENTA "" /* Magenta */
// #define CYAN ""    /* Cyan */
// #define WHITE ""   /* White */

// #define BOLDBLACK ""   /* Bold Black */
// #define BOLDRED ""     /* Bold Red */
// #define BOLDGREEN ""   /* Bold Green */
// #define BOLDYELLOW ""  /* Bold Yellow */
// #define BOLDBLUE ""    /* Bold Blue */
// #define BOLDMAGENTA "" /* Bold Magenta */
// #define BOLDCYAN ""    /* Bold Cyan */
// #define BOLDWHITE ""   /* Bold White */

#define RESET ""
#define BLACK ""   /* Black */
#define RED ""     /* Red */
#define GREEN ""   /* Green */
#define YELLOW ""  /* Yellow */
#define BLUE ""    /* Blue */
#define MAGENTA "" /* Magenta */
#define CYAN ""    /* Cyan */
#define WHITE ""   /* White */

#define BOLDBLACK ""   /* Bold Black */
#define BOLDRED ""     /* Bold Red */
#define BOLDGREEN ""   /* Bold Green */
#define BOLDYELLOW ""  /* Bold Yellow */
#define BOLDBLUE ""    /* Bold Blue */
#define BOLDMAGENTA "" /* Bold Magenta */
#define BOLDCYAN ""    /* Bold Cyan */
#define BOLDWHITE ""   /* Bold White */

#endif //FILESYSTEM_TOOLS_H
