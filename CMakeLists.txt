cmake_minimum_required(VERSION 3.16)
project(app)

set(CMAKE_CXX_STANDARD 17)

add_executable(app
        src/main.cpp

        src/DiskManager.cpp src/DiskManager.h
        src/FileSystemCore.cpp src/FileSystemCore.h
        src/CommandLineInterface.cpp src/CommandLineInterface.h
        src/Shell.cpp src/Shell.h

        src/include/Constraints.h
        src/include/Data.h

        src/model/FreeBlockStack.h src/model/FreeBlockStack.cpp
        src/model/Vim.h src/model/Vim.cpp
)
