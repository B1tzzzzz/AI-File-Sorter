void swap(void *p1, void *p2, int size) {
    void *tmp = malloc(size);
    if (tmp == NULL) return;
    
    memcpy(temp, p1, size);
    memcpy(p1, p2, size);
    memcpy(p2, temp, size);

    free(temp);
}

int main() {
    int a, b;
    swap(&a, &b, sizeof(int));
}