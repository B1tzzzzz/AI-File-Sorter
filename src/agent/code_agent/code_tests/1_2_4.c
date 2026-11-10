#include <stdio.h>
int main() {
    int n = 0;
    double sum = 0;
    while (1) {
        double current = 0;
        printf("Enter the element of the sequence: ");
        if (scanf("%lf", &current)) {
            n++;
            sum += current;
        }
        else {
            break;
        }
    }

    if (!n) {
        printf("Average of empty sequence is 0.");
    }
    else {
        printf("Average of the entered sequence is %.5lf.", sum / (double)n);
    }
    return 0;
}