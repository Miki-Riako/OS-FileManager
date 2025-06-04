cmake_minimum_required(VERSION 3.16)
project(app)

set(CMAKE_CXX_STANDARD 17)

add_executable(app
        src/main.cpp

        src/DiskManager.cpp src/DiskManager.h
        src/FileSystemCore.cpp src/FileSystemCore.h
        src/CommandLineInterface.cpp src/CommandLineInterface.h
        src/Shell.cpp src/Shell.h

        src/Constraints.h
        src/Tools.h

        src/entity/FreeBlockStack.h src/entity/FreeBlockStack.cpp
        src/entity/Vim.h src/entity/Vim.cpp

        src/entity/Directory.h
        src/entity/FileSystemCoreInfo.h
        src/entity/FileIndex.h
        src/entity/INode.h
        src/entity/User.h)
