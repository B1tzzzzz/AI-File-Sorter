#include <stdio.h>
#include <stdlib.h>
int main() {
    int cntWonderful = 0, lastWonderful = 0; //"Wonderful" numbers are integer numbers divisible by 3, which have more than 3 digits in their representation
    while (1) {
        int current = 0;
        printf("Enter the element of the sequence: ");
        if (scanf("%d", &current)) {
            if (!(abs(current) % 5) && abs(current) > 999) {
                cntWonderful++;
                lastWonderful = current;
            }
        }
        else {
            break;
        }
    }

    printf("The number of wonderful numbers is %d.\n", cntWonderful);
    if (!cntWonderful) {
        printf("The sequence doesnt have any wonderful numbers.");
    }
    else {
        printf("The last wonderful element is %d.", lastWonderful);
    }
    return 0;
}