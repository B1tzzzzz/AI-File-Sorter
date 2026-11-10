#include "avl_tree.h"

size_t get_height(avl_tree *root) {
    return (root) ? root->h : 0;
}
void fix_height(avl_tree *root) {
    size_t hl = get_height(root->l), hr = get_height(root->r);
    root->h = (hl > hr) ? hl + 1 : hr + 1;
}

int balance_factor(avl_tree *root) {
    return get_height(root->r) - get_height(root->l);
}

avl_tree* r_rotation(avl_tree *root) {
    avl_tree *root_l = root->l;
    root->l = root_l->r;
    root_l->r = root;
    fix_height(root);
    fix_height(root_l);
    return root_l;
}

avl_tree* l_rotation(avl_tree *root){
    avl_tree *root_r = root->r;
    root->r = root_r->l;
    root_r->l = root;
    fix_height(root);
    fix_height(root_r);
    return root_r;
}

avl_tree* balance_tree(avl_tree *root) {
    int bfactor = balance_factor(root);
    if (bfactor == -2) {
         if (balance_factor(root->l) > 0) {
            root->l = l_rotation(root->l);
        }
        return r_rotation(root);
    }

    else if (bfactor == 2) {
        if (balance_factor(root->r) < 0) {
            root->r = r_rotation(root->r);
        }
        return l_rotation(root);
    }
}

avl_tree* lower_bound(avl_tree *root, int value){
    avl_tree *node = root;
    return node;
}


bool insert(avl_tree *root, int value){
    avl_tree *node = root;
    while (1) {
        if (value > node->value) {
            if (!node->r) break;
            node = node->r;
        }
        else if (value < node->value) {
            if (!node->l) break;
            node = node->l;
        }
        else return 0;
    }
    if (node->value < value) {
        node->r = (avl_tree*)malloc(sizeof(avl_tree));
        node->r->l = node->r->r = NULL;
        node->r->value = value;
        node->h = 0;
        
    }
    return 1;
}

void remove(avl_tree *root, int value){

}

int find_min(avl_tree *root){

}

int find_max(avl_tree *root){

}
