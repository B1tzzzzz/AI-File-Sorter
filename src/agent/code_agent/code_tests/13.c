#include <stdio.h>
#include <math.h>

int binPow(int x, int p) {
    if (!p)
        return 1;
        
    if (p & 1) 
        return binPow(x, p - 1) * x;

    else {
        int res = binPow(x, p / 2);
        return res * res;
    }
}
int main(){
    int num, power;
    printf("Enter the number and the power to which you want to raise it: ");
    if (scanf("%d %d", &num, &power) != 2) {
        printf("Incorrect input.");
        return 0;
    }
    printf("The result of raising the number %d to the power of %d: %d", num, power, binPow(num, power));
}