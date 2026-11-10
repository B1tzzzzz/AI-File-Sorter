#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <queue>
#include <deque>
#include <map>
#include <set>
#include <cmath>
#include <random>
#include <bitset>
#include <string>
#include <iomanip>
#include <cstring>

#define fi first
#define pi pair<long long, long long>
#define se second
using namespace std;
typedef long long ll;
const int maxN = 21, INF = 2e9;

int dp[1 << maxN] = { 0 };
void solve()
{
    int n, k; cin >> n >> k;
    vector <int> a(n), b(n), c(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i] >> b[i] >> c[i];
    }

    for (int mask = 1; mask < (1 << n); mask++) {
        dp[mask] = INF;
    }
    dp[0] = k;
    
    for (int mask = 1; mask < (1 << n); mask++) {
        for (int u = 0; u < n; u++) {
            int mask2 = mask ^ (1 << u);
            if (!((mask >> u) & 1) || dp[mask2] > b[u] || dp[mask2] < a[u]) 
                continue;
            dp[mask] = dp[mask2] + c[u];
        }
    }

    int ans = 0;
    for (int mask = 1; mask < (1 << n); mask++) {
        if (ans < __builtin_popcount(mask) && dp[mask] != INF)
            ans = __builtin_popcount(mask);
    }

    cout << ans;
}

signed main()
{
    ios_base::sync_with_stdio(0);
    cin.tie(0);
    cout.tie(0);
    long long tcurCnt = 1;
    while (tcurCnt--)
    {
        solve();
    }

    return 0;
}