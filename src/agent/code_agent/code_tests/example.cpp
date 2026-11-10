#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <queue>
#include <string>
#include <set>
#include <unordered_set>
#include <unordered_map>
#include <cmath>
#include <iomanip>
#pragma GCC optimize("O3")

using namespace std;

class DSU
{
public:
    vector <int> parent;
    vector <int> size;
    DSU(int n)
    {
        parent.resize(n + 1);
        size.resize(n + 1);
        for (int i = 1; i < n + 1; i++)
        {
            parent[i] = i;
            size[i] = 1;
        }
    }

    int leader(int v)
    {
        return (parent[v] == v) ? v : parent[v] = leader(parent[v]);
    }

    void unite(int a, int b)
    {
        a = leader(a), b = leader(b);
        if (size[a] > size[b]) { swap(a, b); }
        size[b] += size[a];
        parent[a] = b;
    }
};

int main()
{
    cout << "Amount of nodes: ";
    int n; cin >> n;
    DSU dsu(n);

    cout << "Amount of operations: ";
    int q; cin >> q;
    for (int j = 0; j < q; j++)
    {
        cout << j + 1 << ": ";
        string inp; cin >> inp;
        if (inp == "unite")
        {
            int a, b; cin >> a >> b;
            dsu.unite(a, b);
        }

        else if (inp == "leader")
        {
            int v; cin >> v;
            cout << dsu.leader(v) << endl;
        }
        else
        {
            cout << "WTF?" << endl;
        }
    }

    
}
