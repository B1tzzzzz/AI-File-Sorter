#include <stdio.h>
int main() {
    double min = 0;
    int minCnt = 1;
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
            if (min > current) {
                min = current;
                minCnt = 1;
            }
            else if (min == current) {//другое сравнение
                minCnt++;
            }
        }
        else {
            break;
        }
    }

    printf("The number of minimuns in sequence is %d.", minCnt);
    return 0;
}