#include <stdio.h>
int main() {
    double sum = 0, sumOfSquares = 0;
    int n = 0;
    while (1) { 
        double current = 0;
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            n++;
            sum += current;
            sumOfSquares += current * current;
        }
        else {
            break;
        }
    }
    double result = (sumOfSquares - sum * sum / (double)n) / (double)n;
    printf("The dispersion of the sequence is %lf.", result);
}