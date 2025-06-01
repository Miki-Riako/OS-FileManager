// converter.cpp
#include <iostream>
#include <string>
#include <algorithm> // For std::transform
#include <cctype>    // For std::toupper

int main() {
    std::string line;
    // Continuously read lines from standard input
    while (std::getline(std::cin, line)) {
        // Convert the line to uppercase
        std::transform(
            line.begin(),
            line.end(),
            line.begin(),
            [](unsigned char c){
                return std::toupper(c);
            }
        );
        // Print the uppercase line to standard output
        // std::endl flushes the buffer, which is important for Python to read it promptly
        std::cout << line << std::endl;
    }
    return 0;
}
