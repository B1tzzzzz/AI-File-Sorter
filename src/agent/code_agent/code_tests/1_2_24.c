#include <stdio.h>
#include <stdlib.h>
int main() {
    double min = 0, max = 0;
    int n = 1;
    double current = 0;
    if (scanf("%lf", &current)) {
        max = current;
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
            if (current > max) {
                max = current;
            }
            if (current < min) {
                min = current;
            }
        }
        else {
            break;
        }
    }

    printf("The maximum of the sequence is %d.\n", max);
    printf("The minimum of the sequence is %d.\n", min);
    return 0;
}