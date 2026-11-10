#include <stdio.h>
#include <stdlib.h>
int main() {
    double max = 0;
    int n = 1, firstMax = 1;
    double current = 0;
    if (scanf("%lf", &current)) {
        max = current;
    }
    else {
        printf("Empty sequence.");
        return 0;
    }
    
    while (1) {
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            n++;
            if (current > max) {
                max = current;
                firstMax = n;
            }
        }
        else {
            break;
        }
    }

    printf("The position of the first maximum in the sequence is %d.\n", firstMax);
    return 0;
}