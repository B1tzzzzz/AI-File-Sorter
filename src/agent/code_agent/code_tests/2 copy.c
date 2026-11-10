#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

bool input_n_shift(int *n, int *shift);
bool input_array(int* arr,  int n);
void swap(int* a, int* b);
void shift_array(int *arr, int n, int shift);
void print_array(const int *arr, int n);

int main() {
    int n = 0, shift = 0;
    if (!input_n_shift(&n, &shift)) {
        return 1;
    }

    int* arr = (int*)malloc(n * sizeof(int));
    if (arr == NULL) {
        printf("Error allocating memory.\n");
        return 1;
    }

    if (!input_array(arr,  n)) {
        free(arr);
        return 1;
    }

    shift_array(arr, n, shift);
    print_array(arr, n);
    free(arr);
    return 0;
}

bool input_n_shift(int *n, int *shift) {
    printf("Enter the lenght of an array: ");
    if (scanf("%d", n) != 1 || (*n) <= 0) {
        printf("Incorrect input.\n");
        return 0;
    }

    printf("Enter the number of steps to cyclically shift an array to the right: ");
    if (scanf("%d", shift) != 1 || (*shift) < 0) {
        printf("Incorrect input.\n");
        return 0;
    }
    return 1;
}

bool input_array(int* arr,  int n) {
    for (int i = 0; i < n; i++) {
        int current;
        printf("Enter element of an array: ");
        if (scanf("%d", &current) == 1) {
            arr[i] = current;
        }
        else {
            printf("Incorrect input.\n");
            return 0;
        }
    }
    return 1;
}

void print_array(const int *arr, int n) {
    printf("Cyclically shifted array to the right: ");
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

void swap(int *a, int *b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

void shift_array(int *arr, int n, int shift){
    int cnt = 0, i = 0, j = 0;
    while (cnt < n) {
        i = j;
        int tmp = arr[i];
        while (1) {
            i = (i + shift) % n;
            cnt++;
            swap(&arr[i], &tmp);
            if (i == j || cnt == n) break;
        }
        j++;
        if (cnt == n) break;
    }
}
