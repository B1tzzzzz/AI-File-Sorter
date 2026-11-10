#include <stdio.h>
#include <stdbool.h>
#include <math.h>
#define E 1e-12
int main() {
    double current, gap, prev;
    printf("Enter the element of the sequence: ");
    if (scanf("%lf", &current)) {
        prev = current;
    }
    else {
        printf("Incorrect input.");
        return 0;
    }
    
    printf("Enter the element of the sequence: ");
    if (scanf("%lf", &current)) {
        gap = current - prev;
        prev = current;
    }
    else {
        printf("This sequence is an ariphmetic progression.");
        return 0;
    }

    bool isAriphmeticProggresion = 1;
    while (1) { 
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            if (!isAriphmeticProggresion) continue;
            if (fabs(current - prev - gap) > E) {
                isAriphmeticProggresion = 0;
            }
        }
        else {
            break;
        }
    }

    if (isAriphmeticProggresion) {
        printf("This sequence is an ariphmetic progression.");
    }
    else {
        printf("This sequence is not an ariphmetic progression.");
    }
    return 0;
}