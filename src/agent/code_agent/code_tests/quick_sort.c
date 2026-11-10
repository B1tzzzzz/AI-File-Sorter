#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

bool input_n(int *n);
bool input_array(int* arr,  int n);
void swap(int *a, int *b);
int partition(int *arr, int l, int r, int pivot);
void quick_sort(int *arr, int l, int r);
void print_array(int *arr, int n);


int main() {
    int n = 0;
    if (!input_n(&n)) {
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
    
    quick_sort(arr, 0, n);
    print_array(arr, n);
    free(arr);
    return 0;
}

bool input_n(int *n) {
    printf("Enter the lenght of an array: ");
    if (scanf("%d", n) != 1 || (*n) <= 0) {
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

void swap(int *a, int *b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

int partition(int *arr, int l, int r, int pivot) {
    int j = l;
    for (int i = l; i < r; i++) {
        if (arr[i] < arr[pivot]) {
            swap(&arr[j++], &arr[i]);
        }
    }
    swap(&arr[pivot], &arr[j]);
    return j;
}

void quick_sort(int *arr, int l, int r) {
    if (l >= r - 1) {
        return;
    }
    int pivot = r - 1;
    int split = partition(arr, l, r, pivot);
    quick_sort(arr, l, split);
    quick_sort(arr, split + 1, r);
}

void print_array(int *arr, int n) {
    printf("Sorted array: ");
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}
