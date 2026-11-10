#include <stdio.h>
#include <stdlib.h>
int main() {
    int cntEven = 0, cntOdd = 0;
    while (1) {
        int current = 0;
        printf("Enter the element of the sequence: ");
        if (scanf("%d", &current)) {
            if (abs(current) & 1) {
                cntOdd++;
            }
            else {
                cntEven++;
            }
        }
        else {
            break;
        }
    }

    printf("The number of even numbers is %d.\n", cntEven);
    printf("The number of odd numbers is %d.", cntOdd);
    return 0;
}