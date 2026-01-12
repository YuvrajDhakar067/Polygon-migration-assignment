#include "testlib.h"

int main(int argc, char* argv[]) {
    setName("compare sequences of doubles with 10^-6 precision");
    registerTestlibCmd(argc, argv);

    int count = 0;
    while (!ans.seekEof()) {
        count++;
        double j = ans.readDouble();
        double p = ouf.readDouble();

        // testlib's built-in comparison for absolute and relative error
        if (!doubleCompare(j, p, 1e-6)) {
            quitf(_wa, "%d-th number differs - expected: '%.10f', found: '%.10f'", count, j, p);
        }
    }

    if (!ouf.seekEof()) {
        quitf(_pe, "Extra tokens in output");
    }

    quitf(_ok, "%d numbers checked", count);
    return 0;
}