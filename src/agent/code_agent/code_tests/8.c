#include <stdio.h>
#include <stdlib.h>
void* xmalloc(size_t size) {
    void *p = malloc(size);
    if (p == NULL) {
        perror("malloc");
        exit(EXIT_FAILURE);
    }
    return p;
}

void merge(int *arr, int l, int mid, int r) {
    int* tmpArr = xmalloc((r - l + 1) * sizeof(int));
    int i = l, j = mid, k = 0;
    while (i < mid && j < r) {
        if (arr[i] <= arr[j]) {
            tmpArr[k++] = arr[i++];
        }
        else {
            tmpArr[k++] = arr[j++];
        }
    }

    while (i < mid) {
        tmpArr[k++] = arr[i++];
    }

    while (j < r) {
        tmpArr[k++] = arr[j++];
    }

    for (int i = l; i < r; i++) {
        arr[i] = tmpArr[i - l];
    }
    free(tmpArr);
}
void merge_sort(int *arr, int l, int r) {
    if (l >= r - 1)  {
        return;
    }
    int mid = l + (r - l) / 2;
    merge_sort(arr, l, mid);
    merge_sort(arr, mid, r);
    merge(arr, l, mid, r);
}

int main() {
    int n; 
    printf("Enter the lenght of an array: ");
    scanf("%d", &n);
    int *arr = (int*)xmalloc(n * sizeof(int));
    for (int i = 0; i < n; i++) {
        int current;
        printf("Enter element of an array: ");
        if (scanf("%d", &current) == 1) {
            arr[i] = current;
        }
        else {
            printf("Incorrect input.");
            exit(EXIT_FAILURE);
        }
    }
    
    merge_sort(arr, 0, n);
    printf("Sorted array: ");
    for (int i = 0; i < n - 1; i++) {
        printf("%d, ", arr[i]);
    }
    printf("%d.", arr[n - 1]);
    free(arr);
}