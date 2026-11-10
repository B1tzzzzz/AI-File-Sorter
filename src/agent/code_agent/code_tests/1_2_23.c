#include <stdio.h>
#include <math.h>
#define E 1e-12
int main() {
    int lastIdxEqualToX = -1, n = 0;
    double x = 0;
    printf("Enter the first number: ");
    if (scanf("%lf", &x) != 1) {
        printf("Incorrect input.");
        return 0;
    }
    while (1) {
        double current = 0;
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            n++;
            if (fabs(current - x) < E) {
                lastIdxEqualToX = n;
            }
        }
        else {
            break;
        }
    }

    printf("The position of a number that is equal to the last number in a sequence is %d.\n", lastIdxEqualToX);
    return 0;
}