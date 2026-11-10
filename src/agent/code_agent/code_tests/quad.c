#include <stdio.h>
#include <math.h>
#define E 1e-12
int eq_quadr(double a, double b, double c, double *x1, double *x2) {
    if (a == 0.0) {
        if (b == 0.0) {
            return -2;
        }
        else {
            *x1 = -c / b;
            *x2 = *x1;
            return 0; 
        }
    }

    double p = b / a;
    double q = c / a;
    double D = p * p - 4.0 * q;

    if (D < -E) {
        *x1 = -p / 2.0;
        *x2 = sqrt(-D) / 2.0;
        return -1;
    } 
    else if (fabs(D) <= E) {
        *x1 = -p / 2.0;
        *x2 = *x1;
        return 0;
    } 
    else {
        double sqrtD = sqrt(D);
        double t1, t2;
        
        if (p > E) {
            t1 = (-p - sqrtD) / 2.0;
        } 
        else {
            t1 = (-p + sqrtD) / 2.0;
        }

        if (fabs(t1) > E) {
            t2 = q / t1;
        } 
        else {
            t2 = 0.0;
        }
        
        *x1 = t1;
        *x2 = t2;
        
        return 1;
    }
}

int main() {
    double a, b, c;
    double x1, x2;
    int res;

    printf("Enter the coefficients of quadratic equation: ");
    if (scanf("%lf %lf %lf", &a, &b, &c) != 3) {
        printf("Incorrect input.");
        return 0;
    }
    
    res = eq_quadr(a, b, c, &x1, &x2);
    if (res == 1) {
        printf("Found 2 solutions:\nx1 = %.5lf\nx2 = %.5lf", x1, x2);
    }
    else if (res == 0) {
        printf("Found 1 solution:\nx1 = %.5lf", x1);
    }
    else if (res == -1) {
        printf("Found complex solution:\n Re:%.5lf\nIm:%.5lf", x1, x2);
    }
    else {
        printf("No solutions.");
    }

    return 0;
}