#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

bool input_n(int *n);
bool input_array(int* arr,  int n);
long long merge(int *arr, int l, int mid, int r);
long long count_inversions(int *arr, int l, int r);


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
    
    long long res = count_inversions(arr, 0, n);
    printf("The amount of inversions is ");
    printf("%lld.\n", res);
    free(arr);
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

long long merge(int *arr, int l, int mid, int r) {
    long long res = 0;
    int* tmpArr = malloc((r - l + 1) * sizeof(int));
    if (tmpArr == NULL) {
        printf("Error allocating memory.\n");
        exit(1);
    }
    int i = l, j = mid, k = 0;
    while (i < mid && j < r) {
        if (arr[i] <= arr[j]) {
            tmpArr[k++] = arr[i++];
            res += j - mid;
        }
        else {
            tmpArr[k++] = arr[j++];
        }
    }

    while (i < mid) {
        tmpArr[k++] = arr[i++];
        res += j - mid;
    }

    while (j < r) {
        tmpArr[k++] = arr[j++];
    }

    for (int i = l; i < r; i++) {
        arr[i] = tmpArr[i - l];
    }
    free(tmpArr);
    return res;
}

long long count_inversions(int *arr, int l, int r) {
    if (l >= r - 1)  {
        return 0;
    }
    int mid = l + (r - l) / 2;
    long long res = 0;
    res += count_inversions(arr, l, mid);
    res += count_inversions(arr, mid, r);
    res += merge(arr, l, mid, r);
    return res;
}