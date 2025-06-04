#include "Shell.h"

int main() {
    Shell s;
    s.cmd_login();
    while (!s.isExit) {
        s.exec();
    }
    return 0;
}
