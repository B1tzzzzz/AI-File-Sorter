#include <stdio.h>
int main() {
    double min = 0;
    int firstMin = 1, lastMin = 1;
    int n = 1;
    double current = 0;

    if (scanf("%lf", &current)) {
        min = current;
    }
    else {
        printf("Empty sequence.");
        return 0;
    }

    while (1) { 
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            n++;
            if (min > current) {
                min = current;
                firstMin = lastMin = n;
            }
            else if (min == current) {
                lastMin = n;
            }
        }
        else {
            break;
        }
    }

    printf("The position of the first minimum is %d.", firstMin);
    printf("The position of the last minimum is %d.", lastMin);
}